"""
Legal APK download source integration.
Supports APKPure, APKMirror, and open-source APK repositories.
"""

import aiohttp
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class APKPureSource:
    """APKPure API integration for legal APK sourcing"""
    
    BASE_URL = "https://apkpure.com"
    
    async def search_app(self, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for app on APKPure by package ID.
        
        Args:
            package_id: Android package ID (e.g., com.whatsapp)
        
        Returns:
            App data with download link or None
        """
        try:
            # APKPure doesn't have a public API, but we can construct direct links
            # In production, use their affiliate API if available
            apkpure_url = f"{self.BASE_URL}/app/{package_id}"
            
            # Fallback: construct direct CDN link for popular apps
            # This should be verified to ensure app actually exists on APKPure
            download_url = f"https://d.apkpure.com/b/{package_id}"
            
            return {
                "source": "apkpure",
                "package_id": package_id,
                "app_url": apkpure_url,
                "download_url": download_url,
                "affiliate_url": apkpure_url  # Use APKPure link for ad revenue
            }
        except Exception as e:
            logger.error(f"Error searching APKPure: {str(e)}")
            return None


class APKMirrorSource:
    """APKMirror scraping for legal APK sourcing"""
    
    BASE_URL = "https://www.apkmirror.com"
    
    async def search_app(self, app_name: str, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for app on APKMirror.
        
        Args:
            app_name: Human-readable app name
            package_id: Android package ID
        
        Returns:
            App data with download link or None
        """
        try:
            # APKMirror URL structure
            slug = app_name.lower().replace(" ", "-")
            app_url = f"{self.BASE_URL}/apk/{slug}/{package_id}/"
            
            # APKMirror generates affiliate links for monetization
            affiliate_url = app_url
            
            return {
                "source": "apkmirror",
                "package_id": package_id,
                "app_url": app_url,
                "affiliate_url": affiliate_url,
                "requires_manual_verification": True  # Must verify app exists
            }
        except Exception as e:
            logger.error(f"Error searching APKMirror: {str(e)}")
            return None


class OpenSourceAPKSource:
    """Open-source APK repositories (legal alternatives)"""
    
    SOURCES = {
        "f_droid": {
            "name": "F-Droid",
            "url": "https://f-droid.org",
            "api": "https://f-droid.org/api/v1",
            "description": "Free and open-source apps for Android"
        },
        "fdroid_archive": {
            "name": "F-Droid Archive",
            "url": "https://archive.org/details/fdroid",
            "description": "Open-source Android apps archive"
        }
    }
    
    async def search_app(self, app_name: str, package_id: str) -> Optional[Dict[str, Any]]:
        """
        Search for app in open-source repositories.
        
        Args:
            app_name: App name
            package_id: Package ID
        
        Returns:
            App data if found in open-source repos
        """
        try:
            # Query F-Droid API
            fdroid_data = await self._search_fdroid(package_id)
            if fdroid_data:
                return fdroid_data
            
            return None
        except Exception as e:
            logger.error(f"Error searching open-source sources: {str(e)}")
            return None
    
    async def _search_fdroid(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Search F-Droid repository"""
        try:
            url = f"{self.SOURCES['f_droid']['api']}/packages/{package_id}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        # Get latest version
                        if data.get("packages"):
                            latest = data["packages"][0]
                            
                            return {
                                "source": "f_droid",
                                "package_id": package_id,
                                "app_url": f"{self.SOURCES['f_droid']['url']}/packages/{package_id}",
                                "app_name": data.get("name"),
                                "download_url": f"{self.SOURCES['f_droid']['url']}/repo/{latest.get('apkFileName')}",
                                "version": latest.get("versionName"),
                                "open_source": True,
                                "is_legal": True,
                                "attribution": f"Open-source app from {self.SOURCES['f_droid']['name']}"
                            }
        except Exception as e:
            logger.debug(f"F-Droid search failed: {str(e)}")
            return None


class DownloadSourceManager:
    """Manages legal download sources in priority order"""
    
    SOURCES_PRIORITY = [
        OpenSourceAPKSource(),  # Priority 1: Legal open-source
        APKMirrorSource(),      # Priority 2: Legal aggregator
        APKPureSource(),        # Priority 3: Popular aggregator
    ]
    
    async def find_download_link(
        self,
        app_name: str,
        package_id: str,
        version_name: str = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find legal download link for an app using priority sources.
        
        Args:
            app_name: Human-readable app name
            package_id: Android package ID
            version_name: Optional specific version
        
        Returns:
            Download link data or None
        """
        for source in self.SOURCES_PRIORITY:
            try:
                result = await source.search_app(app_name, package_id)
                if result:
                    logger.info(f"Found download link for {package_id} from {result.get('source')}")
                    return result
            except Exception as e:
                logger.warning(f"Error searching source {source.__class__.__name__}: {str(e)}")
                continue
        
        logger.warning(f"Could not find legal download link for {package_id}")
        return None
    
    @staticmethod
    def build_redirect_download_url(
        app_id: str,
        version_id: str,
        source_url: str
    ) -> str:
        """
        Build redirect URL for tracking downloads.
        This allows proper ad serving and analytics.
        
        Args:
            app_id: App UUID
            version_id: Version UUID
            source_url: Actual download URL
        
        Returns:
            Redirect download URL
        """
        # Backend endpoint that redirects to actual source
        # Allows tracking, ad serving, countdown page
        return f"/api/v1/download/redirect/{app_id}/{version_id}"


# Singleton instance
download_manager = DownloadSourceManager()


async def resolve_app_download(
    app_name: str,
    package_id: str,
    app_type: str = "android"
) -> Optional[Dict[str, Any]]:
    """
    Resolve download link for an app respecting legal constraints.
    
    Returns:
        {
            "download_url": "https://...",
            "source": "apkmirror|apkpure|f_droid|official",
            "is_legal": bool,
            "attribution": "source name",
            "requires_affiliate": bool
        }
    """
    if app_type != "android":
        logger.warning(f"Download resolution only supports Android apps, got {app_type}")
        return None
    
    result = await download_manager.find_download_link(app_name, package_id)
    return result
