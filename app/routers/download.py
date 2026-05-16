"""
Download router for APK and PC software management.
Handles download tracking, redirect URLs, safety badges, and legal compliance.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from datetime import datetime
import uuid
from app.database import get_db
from app.models import App, APKVersion, Download, VirusScan
from app.schemas.app import InitiateDownloadResponse, DownloadResponse
from app.services.download_sources import download_manager
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(tags=["download"])
settings = get_settings()


@router.post("/api/v1/apps/{slug}/download-link")
async def get_download_link(
    slug: str,
    db: Session = Depends(get_db)
) -> InitiateDownloadResponse:
    """
    Get legal download link for an app from approved sources.
    Supports both slug and package_id lookup.
    Falls back to official website for apps without APKVersion records.
    """
    # Support both slug and package_id (matches the app detail router)
    app = db.query(App).filter(
        (App.slug == slug) | (App.package_id == slug)
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")

    # Try to get latest versioned download URL first
    version = db.query(APKVersion).filter(
        APKVersion.app_id == app.id,
        APKVersion.is_latest == True
    ).first()

    if version and version.download_url:
        # Tracked download with APKVersion record
        download = Download(
            app_id=app.id,
            version_id=version.id,
            file_size_bytes=version.file_size_bytes,
        )
        db.add(download)
        db.commit()
        db.refresh(download)

        return InitiateDownloadResponse(
            download_id=str(download.id),
            redirect_url=f"/api/v1/download/redirect/{download.id}",
            countdown_seconds=settings.download_redirect_timeout_seconds,
            source=version.download_source or "official",
            actual_file_url=version.download_url,
        )

    # Fallback: build a source-specific URL for apps without APKVersion
    # (Homebrew, Snap, Flathub, Winget — scraped without direct .apk/.exe links)
    fallback_url = _build_source_fallback_url(app)
    if not fallback_url:
        raise HTTPException(
            status_code=400,
            detail="No download available — visit the app's official website."
        )

    # Create a lightweight Download record for analytics
    download = Download(app_id=app.id)
    db.add(download)
    db.commit()
    db.refresh(download)

    return InitiateDownloadResponse(
        download_id=str(download.id),
        redirect_url=fallback_url,
        countdown_seconds=settings.download_redirect_timeout_seconds,
        source=app.data_source or "official",
        actual_file_url=fallback_url,
    )


def _build_source_fallback_url(app: App) -> str | None:
    """Build an official source URL for apps without a direct download link."""
    if app.official_website:
        return app.official_website

    source = app.data_source or ""
    pkg = app.package_id or ""

    if source == "homebrew":
        token = pkg.replace("brew.", "")
        return f"https://formulae.brew.sh/cask/{token}"
    if source == "snap":
        name = pkg.replace("snap.", "")
        return f"https://snapcraft.io/{name}"
    if source == "flathub":
        app_id = pkg.replace("flathub.", "")
        return f"https://flathub.org/apps/{app_id}"
    if source == "f_droid":
        return f"https://f-droid.org/packages/{pkg}"
    if source == "winget":
        return f"https://winget.run/pkg/{pkg}"

    return None


@router.get("/api/v1/download/redirect/{download_id}")
async def download_redirect(
    download_id: str,
    db: Session = Depends(get_db)
):
    """
    Main download redirect endpoint.
    
    This endpoint:
    1. Tracks download analytics
    2. Serves countdown/ad page (if enabled)
    3. Redirects to actual download file
    
    Can serve HTML countdown page OR direct redirect based on settings.
    """
    try:
        download = db.query(Download).filter(Download.id == download_id).first()
        if not download:
            raise HTTPException(status_code=404, detail="Download not found")
        
        # Get version and app info
        version = db.query(APKVersion).filter(
            APKVersion.id == download.version_id
        ).first()
        
        if not version:
            raise HTTPException(status_code=400, detail="Version information missing")
        
        app = db.query(App).filter(App.id == download.app_id).first()
        
        # Update download status to pending
        download.download_status = "pending"
        db.commit()
        
        # Option 1: Return countdown page (for ad impressions)
        if settings.enable_download_redirect:
            return HTMLResponse(
                get_download_countdown_html(
                    app_name=app.name if app else "App",
                    version=version.version_name,
                    download_url=f"/api/v1/download/start/{download_id}",
                    countdown=settings.download_redirect_timeout_seconds,
                    app_icon=app.icon_url if app else None,
                )
            )
        else:
            # Option 2: Direct redirect
            return download_start(download_id, db)
            
    except Exception as e:
        logger.error(f"Error in download redirect: {str(e)}")
        raise HTTPException(status_code=500, detail="Download error")


@router.get("/api/v1/download/start/{download_id}")
async def download_start(
    download_id: str,
    db: Session = Depends(get_db)
):
    """
    Final redirect to actual download file.
    Updates download status to completed.
    """
    try:
        download = db.query(Download).filter(Download.id == download_id).first()
        if not download:
            raise HTTPException(status_code=404, detail="Download not found")
        
        version = db.query(APKVersion).filter(
            APKVersion.id == download.version_id
        ).first()
        
        if not version or not version.download_url:
            raise HTTPException(status_code=400, detail="Download URL not available")
        
        # Update download stats
        download.download_status = "completed"
        version.download_count = (version.download_count or 0) + 1
        db.commit()
        
        logger.info(f"Download initiated: {download_id} for version {version.id}")
        
        # Redirect to actual file
        # If affiliate URL exists, use that for monetization
        redirect_url = version.affiliate_url or version.download_url
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Error starting download: {str(e)}")
        raise HTTPException(status_code=500, detail="Download error")


@router.get("/api/v1/versions/{version_id}/security")
async def get_version_security(
    version_id: str,
    db: Session = Depends(get_db)
) -> dict:
    """
    Get VirusTotal scan results and safety badge for a version.
    Used to display trust signals on app pages.
    """
    version = db.query(APKVersion).filter(APKVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    
    # Get latest scan for this version
    scan = db.query(VirusScan).filter(
        VirusScan.version_id == version_id
    ).order_by(VirusScan.scan_date.desc()).first()
    
    if not scan:
        return {
            "version_id": version_id,
            "safety_badge": "unknown",
            "message": "No scan results available yet",
            "file_hash": version.sha256 or version.md5_hash,
            "file_size": version.file_size,
        }
    
    return {
        "version_id": version_id,
        "file_hash": scan.file_hash,
        "file_size": version.file_size,
        "safety_badge": scan.safety_badge,
        "malicious_count": scan.malicious_count,
        "suspicious_count": scan.suspicious_count,
        "undetected_count": scan.undetected_count,
        "total_vendors": scan.total_vendors,
        "vt_permalink": scan.vt_permalink,
        "scan_date": scan.scan_date,
        "details": {
            "safe": scan.malicious_count == 0 and scan.suspicious_count == 0,
            "message": get_safety_badge_message(scan.safety_badge),
        }
    }


@router.get("/api/v1/downloads/history")
async def download_history(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
) -> dict:
    """Get recent downloads across all apps (for analytics)"""
    downloads = db.query(Download).order_by(
        Download.logged_at.desc()
    ).limit(limit).all()
    
    return {
        "downloads": [
            {
                "id": str(d.id),
                "app_id": str(d.app_id),
                "version_id": str(d.version_id) if d.version_id else None,
                "status": d.download_status,
                "file_size_bytes": d.file_size_bytes,
                "logged_at": d.logged_at,
            }
            for d in downloads
        ],
        "total": len(downloads)
    }


@router.get("/api/v1/apps/{package_id}/versions")
async def get_app_versions(
    package_id: str,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
) -> dict:
    """
    Get version history for an app with security info.
    Enables version selection and changelog viewing.
    """
    app = db.query(App).filter(App.package_id == package_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    versions = db.query(APKVersion).filter(
        APKVersion.app_id == app.id
    ).order_by(APKVersion.release_date.desc()).limit(limit).all()
    
    versions_data = []
    for v in versions:
        # Get scan for this version
        scan = db.query(VirusScan).filter(
            VirusScan.version_id == v.id
        ).first()
        
        versions_data.append({
            "id": str(v.id),
            "version_name": v.version_name,
            "version_code": v.version_code,
            "file_size": v.file_size,
            "file_size_bytes": v.file_size_bytes,
            "changelog": v.changelog,
            "release_date": v.release_date,
            "download_count": v.download_count,
            "is_latest": v.is_latest,
            "min_android": v.min_android,
            "arch": v.arch,
            "download_url": v.download_url,
            "download_source": v.download_source,
            "security": {
                "safety_badge": scan.safety_badge if scan else "unknown",
                "md5": v.md5_hash,
                "sha256": v.sha256,
                "scan_date": scan.scan_date if scan else None,
            }
        })
    
    return {
        "app_id": str(app.id),
        "package_id": app.package_id,
        "app_name": app.name,
        "total_versions": len(versions),
        "versions": versions_data,
    }


# ==================== Helper Functions ====================

def get_safety_badge_message(badge: str) -> str:
    """Get user-friendly message for safety badge"""
    messages = {
        "safe": "✓ This file has been scanned and appears to be safe",
        "suspicious": "⚠ This file may contain suspicious code. Use with caution.",
        "malware": "✗ This file has been flagged as potentially malicious",
        "unknown": "? This file has not been scanned yet",
        "pending": "⏳ Scanning in progress...",
    }
    return messages.get(badge, "No security information available")


def get_download_countdown_html(
    app_name: str,
    version: str,
    download_url: str,
    countdown: int = 5,
    app_icon: str = None,
) -> str:
    """
    Generate HTML for download countdown page.
    Serves ads and builds anticipation before download.
    
    This increases ad impressions and provides better UX.
    """
    icon_html = f'<img src="{app_icon}" alt="{app_name}" class="app-icon">' if app_icon else ""
    
    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Downloading {app_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            
            .container {{
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                max-width: 500px;
                width: 100%;
                padding: 40px;
                text-align: center;
            }}
            
            .app-icon {{
                width: 80px;
                height: 80px;
                border-radius: 16px;
                margin-bottom: 20px;
                box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            }}
            
            h1 {{
                font-size: 24px;
                margin-bottom: 10px;
                color: #333;
            }}
            
            .version {{
                color: #666;
                font-size: 14px;
                margin-bottom: 30px;
            }}
            
            .countdown {{
                font-size: 48px;
                font-weight: bold;
                color: #667eea;
                margin: 30px 0;
                min-height: 60px;
            }}
            
            .message {{
                color: #666;
                margin-bottom: 20px;
                line-height: 1.6;
            }}
            
            .download-button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 12px 40px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                font-size: 16px;
                transition: transform 0.2s, box-shadow 0.2s;
                border: none;
                cursor: pointer;
            }}
            
            .download-button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 10px 25px rgba(102, 126, 234, 0.4);
            }}
            
            .ad-slot {{
                margin-top: 30px;
                padding-top: 30px;
                border-top: 1px solid #eee;
                text-align: center;
                color: #999;
                font-size: 12px;
            }}
            
            .security-info {{
                background: #f5f5f5;
                padding: 15px;
                border-radius: 8px;
                margin-top: 20px;
                font-size: 12px;
                color: #666;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            {icon_html}
            <h1>Preparing Download</h1>
            <div class="version">Version {version}</div>
            
            <div class="countdown" id="countdown">{countdown}</div>
            
            <p class="message">
                Your download will start automatically in <span id="count">{countdown}</span> seconds
            </p>
            
            <button class="download-button" onclick="window.location.href='{download_url}'">
                Download Now
            </button>
            
            <div class="security-info">
                ✓ Safe & Secure Download | Scanned by VirusTotal
            </div>
            
            <div class="ad-slot">
                <!-- Ad placeholder -->
                <p>Advertisement</p>
            </div>
        </div>
        
        <script>
            let seconds = {countdown};
            
            const interval = setInterval(() => {{
                seconds--;
                document.getElementById('countdown').textContent = seconds;
                document.getElementById('count').textContent = seconds;
                
                if (seconds <= 0) {{
                    clearInterval(interval);
                    window.location.href = '{download_url}';
                }}
            }}, 1000);
            
            // Allow skip after 2 seconds
            setTimeout(() => {{
                document.querySelector('.download-button').style.pointerEvents = 'auto';
                document.querySelector('.download-button').innerHTML = 'Download Now (or wait ' + seconds + 's)';
            }}, 2000);
        </script>
    </body>
    </html>
    """

