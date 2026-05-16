"""
Admin management endpoints for APKDroid.
Allows manual triggering of the daily sync pipeline and individual scrapers.
"""

from fastapi import APIRouter, HTTPException, Depends, Header, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import App, Category, APKVersion
from app.config import get_settings
import asyncio
import logging

router = APIRouter(tags=["admin"], prefix="/api/v1/admin")
logger = logging.getLogger(__name__)
settings = get_settings()


async def verify_admin(x_admin_key: str = Header(..., description="Admin API key")):
    expected = getattr(settings, "admin_api_key", None) or ""
    if not expected or x_admin_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden: Invalid admin key")
    return x_admin_key


@router.post("/scrape/trigger", dependencies=[Depends(verify_admin)])
async def trigger_scrape(
    source: str = "all",
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """
    Trigger the scraper pipeline.
    source: all | f_droid | snap | flathub | homebrew | chocolatey | winget
    limit: apps per platform (default 50)
    """
    from app.services.legal_scraper import (
        run_daily_sync,
        sync_fdroid_apps,
        sync_snap_apps,
        sync_flathub_apps,
        sync_homebrew_apps,
        sync_chocolatey_apps,
        _auto_describe,
    )

    try:
        if source == "all":
            results = await run_daily_sync(db, limit_per_os=limit)
            return {"status": "success", "results": results}

        elif source == "f_droid":
            n = await sync_fdroid_apps(db, limit=limit)
            return {"status": "success", "android_apps_added": n}

        elif source == "snap":
            n = await sync_snap_apps(db, limit=limit)
            return {"status": "success", "linux_apps_added": n}

        elif source == "flathub":
            n = await sync_flathub_apps(db, limit=limit)
            return {"status": "success", "linux_apps_added": n}

        elif source == "homebrew":
            n = await sync_homebrew_apps(db, limit=limit)
            return {"status": "success", "macos_apps_added": n}

        elif source in ("chocolatey", "winget", "windows"):
            n = await sync_chocolatey_apps(db, limit=limit)
            return {"status": "success", "windows_apps_added": n}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown source: {source}. Use: all | f_droid | snap | flathub | homebrew | chocolatey")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scrape error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-descriptions", dependencies=[Depends(verify_admin)])
async def generate_descriptions(
    limit: int = 500,
    overwrite: bool = False,
    db: Session = Depends(get_db),
):
    """
    Backfill SEO descriptions for all apps missing one.
    overwrite=true regenerates even existing descriptions.
    """
    from app.services.description_generator import generate_description

    query = db.query(App)
    if not overwrite:
        query = query.filter(
            (App.description == None) | (App.description == "") |
            (App.description == "No description available.")
        )
    apps = query.limit(limit).all()

    count = 0
    for app in apps:
        try:
            desc, short = generate_description(
                name=app.name,
                software_type=app.software_type or "android",
                developer=app.developer or "",
                version=app.latest_version or "",
                existing_short_desc=app.short_desc,
            )
            app.description = desc
            if not app.short_desc or overwrite or len(app.short_desc) < 10:
                app.short_desc = short
            count += 1
        except Exception as e:
            logger.warning(f"Description gen failed for {app.name}: {e}")

    db.commit()
    return {
        "status": "success",
        "updated": count,
        "message": f"Generated descriptions for {count} apps",
    }


@router.get("/stats", dependencies=[Depends(verify_admin)])
async def get_stats(db: Session = Depends(get_db)):
    total_apps = db.query(App).count()
    total_categories = db.query(Category).count()
    total_versions = db.query(APKVersion).count()
    no_desc = db.query(App).filter(
        (App.description == None) | (App.description == "")
    ).count()

    by_platform = {
        pt: db.query(App).filter(App.software_type == pt).count()
        for pt in ("android", "linux", "macos", "windows")
    }

    return {
        "total_apps": total_apps,
        "total_categories": total_categories,
        "total_versions": total_versions,
        "apps_without_description": no_desc,
        "apps_by_platform": by_platform,
    }


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Admin API is running"}
