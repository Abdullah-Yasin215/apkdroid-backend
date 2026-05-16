"""
APKDroid Daily Scraper Pipeline.
Scrapes exactly 50 apps per OS per day, auto-generates SEO descriptions for all new apps.
Runs via APScheduler (nightly at 3 AM UTC) AND can be triggered manually.

Sources:
  Android  → F-Droid (per-package endpoint)
  Linux    → Snap Store + Flathub
  macOS    → Homebrew Cask
  Windows  → Chocolatey (OData XML API)
"""

import asyncio
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import App, Category, APKVersion
from app.utils.slug import slugify
import aiohttp

logger = logging.getLogger(__name__)

DAILY_LIMIT_PER_OS = 50   # 50 apps per platform per run


# ─── helpers ────────────────────────────────────────────────────────────────

def _ensure_category(db: Session, name: str, slug: str, icon: str = "📦") -> Category:
    cat = db.query(Category).filter(Category.slug == slug).first()
    if not cat:
        cat = Category(
            id=uuid.uuid4(),
            name=name,
            slug=slug,
            description=f"{name} applications",
            icon=icon,
        )
        db.add(cat)
        db.flush()
    return cat


def _make_slug(name: str, suffix: str = "", db: Session = None) -> str:
    base = slugify(name or "app")[:90]
    slug = f"{base}-{slugify(suffix)[:30]}" if suffix else base
    if not slug or slug.strip("-") == "":
        slug = f"app-{uuid.uuid4().hex[:8]}"
    if db:
        existing = db.query(App).filter(App.slug == slug).first()
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"
    return slug[:120]


def _upsert(db: Session, package_id: str, defaults: dict) -> App:
    app = db.query(App).filter(App.package_id == package_id).first()
    if app:
        for k, v in defaults.items():
            if k not in ("id", "slug", "package_id") and v is not None:
                setattr(app, k, v)
    else:
        app = App(
            id=uuid.uuid4(),
            package_id=package_id,
            slug=_make_slug(defaults.get("name", package_id), package_id, db),
            **{k: v for k, v in defaults.items() if k not in ("id", "slug")},
        )
        db.add(app)
    return app


def _auto_describe(app: App) -> None:
    """Auto-generate SEO description if missing."""
    if app.description and len(app.description) > 50:
        return  # already has a good description
    try:
        from app.services.description_generator import generate_description
        desc, short = generate_description(
            name=app.name,
            software_type=app.software_type or "android",
            developer=app.developer or "",
            version=app.latest_version or "",
            existing_short_desc=app.short_desc,
        )
        app.description = desc
        if not app.short_desc or len(app.short_desc) < 10:
            app.short_desc = short
    except Exception as e:
        logger.debug(f"Description gen error for {app.name}: {e}")


# ═══ ANDROID — F-Droid ═══════════════════════════════════════════════════════

FDROID_POPULAR = [
    "org.mozilla.firefox", "org.torproject.torbrowser", "com.nextcloud.client",
    "org.fdroid.fdroid", "org.videolan.vlc", "com.termux", "net.osmand.plus",
    "org.thoughtcrime.securesms", "com.github.libretube", "org.schabi.newpipe",
    "de.danoeh.antennapod", "com.simplemobiletools.gallery.pro", "org.fossify.phone",
    "org.sufficientlysecure.keychain", "at.bitfire.davdroid", "org.kde.kdeconnect_tp",
    "eu.faircode.email", "com.beemdevelopment.aegis", "org.cryptomator",
    "com.mikifus.padland", "de.westnordost.streetcomplete", "io.ente.auth",
    "com.amaze.filemanager", "com.fsck.k9", "net.mullvad.mullvadvpn",
    "org.lineageos.eleven", "com.google.android.apps.authenticator2",
    "com.menny.android.anysoftkeyboard", "org.adaway", "com.ghostsq.commander",
    "com.ichi2.anki", "org.tasks.copilot", "ru.valle.btchip",
    "com.artifex.mupdf.viewer.app", "org.zotero.android", "it.niedermann.owncloud.notes",
    "me.ccrama.redditslide", "com.wireguard.android", "org.briarproject.briar.android",
    "com.nextcloud.talk2", "org.openhab.habdroid", "org.jellyfin.mobile",
    "com.aurora.store", "app.organicmaps.debug", "io.github.quillpad.quillpad",
    "com.marverenic.music", "de.nulide.findmydevice", "org.witness.sscphase1",
    "com.github.tachiyomix.mangadex", "org.emacs.emacs",
    "org.videolan.vlc", "org.mozilla.fenix", "org.torproject.torbrowser",
    "com.duckduckgo.mobile.android", "org.telegram.messenger", "com.whatsapp",
    "com.facebook.katana", "com.instagram.android", "com.spotify.music",
    "com.netflix.mediaclient", "com.ebay.mobile", "com.amazon.mShop.android.shopping",
    "com.microsoft.teams", "com.zoom.videoconferences", "com.skype.raider",
    "com.viber.voip", "com.snapchat.android", "com.twitter.android",
    "com.zhiliaoapp.musically", "com.pinterest", "com.linkedin.android",
    "com.reddit.frontpage", "com.tumblr", "com.flickr.android",
    "com.google.android.youtube", "com.google.android.apps.docs",
    "com.google.android.apps.maps", "com.google.android.gm",
    "com.google.android.apps.photos", "com.google.android.apps.translate"
]


async def sync_fdroid_apps(db: Session, limit: int = DAILY_LIMIT_PER_OS) -> int:
    import random
    category = _ensure_category(db, "Android Apps", "android-apps", "🤖")
    count = 0
    popular = FDROID_POPULAR.copy()
    random.shuffle(popular)
    async with aiohttp.ClientSession() as session:
        for pkg_id in popular[:limit]:
            try:
                url = f"https://f-droid.org/api/v1/packages/{pkg_id}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

                metadata = data.get("metadata", {})
                releases = data.get("releases", [])
                latest = releases[0] if releases else {}

                name_raw = metadata.get("name") or {}
                name = (name_raw.get("en-US") if isinstance(name_raw, dict) else str(name_raw)) or pkg_id.split(".")[-1].capitalize()
                summary_raw = metadata.get("summary") or {}
                summary = (summary_raw.get("en-US") if isinstance(summary_raw, dict) else str(summary_raw)) or ""
                desc_raw = metadata.get("description") or {}
                description = (desc_raw.get("en-US") if isinstance(desc_raw, dict) else str(desc_raw)) or ""

                app = _upsert(db, pkg_id, {
                    "name": name,
                    "short_desc": summary[:255] or None,
                    "description": description or None,
                    "icon_url": f"https://f-droid.org/repo/{pkg_id}/en-US/icon.png",
                    "latest_version": latest.get("versionName", ""),
                    "software_type": "android",
                    "is_free": True,
                    "data_source": "f_droid",
                    "attribution": "Open-source app from F-Droid",
                    "category_id": category.id,
                    "status": "active",
                    "scraped_at": datetime.utcnow(),
                })
                _auto_describe(app)
                count += 1
                await asyncio.sleep(0.3)
            except Exception as e:
                logger.warning(f"F-Droid {pkg_id}: {e}")
    db.commit()
    logger.info(f"F-Droid: {count} Android apps")
    return count


# ═══ LINUX — Snap Store ══════════════════════════════════════════════════════

async def sync_snap_apps(db: Session, limit: int = DAILY_LIMIT_PER_OS) -> int:
    import random
    category = _ensure_category(db, "Linux Apps", "linux-apps", "🐧")
    count = 0
    queries = ["editor", "browser", "music", "video", "office", "game", "developer", "utility", "system", "security", "finance", "education", "science"]
    random.shuffle(queries)

    async with aiohttp.ClientSession() as session:
        for query in queries:
            if count >= limit:
                break
            try:
                url = "https://api.snapcraft.io/api/v1/snaps/search"
                headers = {"X-Ubuntu-Series": "16", "Accept": "application/hal+json"}
                async with session.get(url, params={"q": query, "limit": min(10, limit - count)},
                                        headers=headers, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()

                for a in data.get("_embedded", {}).get("clickindex:package", []):
                    if count >= limit:
                        break
                    pkg_id = a.get("package_name") or a.get("snap_id")
                    if not pkg_id:
                        continue
                    media = a.get("media", [])
                    icon_url = next((m["url"] for m in media if m.get("type") == "icon"), a.get("icon_url", ""))
                    publisher = a.get("publisher", {})
                    dev = publisher.get("display-name", "") if isinstance(publisher, dict) else str(publisher)

                    app = _upsert(db, f"snap.{pkg_id}", {
                        "name": a.get("title") or pkg_id,
                        "developer": dev,
                        "short_desc": (a.get("summary") or "")[:255] or None,
                        "description": a.get("description") or None,
                        "icon_url": icon_url or None,
                        "latest_version": a.get("version", ""),
                        "software_type": "linux",
                        "is_free": True,
                        "data_source": "snap",
                        "category_id": category.id,
                        "status": "active",
                        "scraped_at": datetime.utcnow(),
                    })
                    _auto_describe(app)
                    count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Snap query '{query}': {e}")

    db.commit()
    logger.info(f"Snap: {count} Linux apps")
    return count


# ═══ LINUX — Flathub ═════════════════════════════════════════════════════════

async def sync_flathub_apps(db: Session, limit: int = DAILY_LIMIT_PER_OS) -> int:
    import random
    category = _ensure_category(db, "Linux Apps", "linux-apps", "🐧")
    count = 0
    start_page = random.randint(1, 10)

    async with aiohttp.ClientSession() as session:
        for page in range(start_page, start_page + 4):
            if count >= limit:
                break
            try:
                url = f"https://flathub.org/api/v2/collection/recently-updated?page={page}&per_page={min(20, limit - count)}"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()

                for a in data.get("hits", data.get("apps", [])):
                    if count >= limit:
                        break
                    pkg_id = a.get("app_id") or a.get("id")
                    if not pkg_id:
                        continue
                    app = _upsert(db, f"flathub.{pkg_id}", {
                        "name": a.get("name") or pkg_id.split(".")[-1],
                        "developer": a.get("developer_name") or a.get("developerName") or "",
                        "short_desc": (a.get("summary") or "")[:255] or None,
                        "icon_url": a.get("icon") or None,
                        "latest_version": a.get("currentReleaseVersion") or "",
                        "software_type": "linux",
                        "is_free": True,
                        "data_source": "flathub",
                        "category_id": category.id,
                        "status": "active",
                        "scraped_at": datetime.utcnow(),
                    })
                    _auto_describe(app)
                    count += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.warning(f"Flathub page {page}: {e}")
                break

    db.commit()
    logger.info(f"Flathub: {count} Linux apps")
    return count


# ═══ macOS — Homebrew Cask ═══════════════════════════════════════════════════

async def sync_homebrew_apps(db: Session, limit: int = DAILY_LIMIT_PER_OS) -> int:
    category = _ensure_category(db, "macOS Apps", "macos-apps", "🍎")
    count = 0
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get("https://formulae.brew.sh/api/cask.json",
                                    timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status != 200:
                    return 0
                casks = await resp.json(content_type=None)
                if not isinstance(casks, list):
                    casks = casks.get("casks", [])
        except Exception as e:
            logger.error(f"Homebrew fetch: {e}")
            return 0

    import random
    random.shuffle(casks)
    for a in casks[:limit]:
        try:
            pkg_id = a.get("token")
            if not pkg_id or a.get("disabled") or a.get("deprecated"):
                continue

            homepage = a.get("homepage", "")
            icon_url = None
            if homepage:
                from urllib.parse import urlparse
                domain = urlparse(homepage).netloc or urlparse(homepage).path
                if domain:
                    domain = domain.replace("www.", "")
                    icon_url = f"https://icon.horse/icon/{domain}"

            app = _upsert(db, f"brew.{pkg_id}", {
                "name": a.get("name", [pkg_id])[0],
                "short_desc": (a.get("desc") or "")[:255] or None,
                "description": a.get("desc") or None,
                "icon_url": icon_url,
                "latest_version": a.get("version", ""),
                "software_type": "macos",
                "is_free": True,
                "data_source": "homebrew",
                "category_id": category.id,
                "status": "active",
                "scraped_at": datetime.utcnow(),
            })
            _auto_describe(app)
            count += 1
        except Exception as e:
            logger.warning(f"Homebrew {a.get('token')}: {e}")

    db.commit()
    logger.info(f"Homebrew: {count} macOS apps")
    return count


# ═══ Windows — Chocolatey ════════════════════════════════════════════════════

async def sync_chocolatey_apps(db: Session, limit: int = DAILY_LIMIT_PER_OS) -> int:
    from app.services.chocolatey_scraper import sync_chocolatey_apps as _choco
    n = await _choco(db, limit=limit)
    # Auto-describe new windows apps
    new_apps = db.query(App).filter(
        App.software_type == "windows",
        (App.description == None) | (App.description == "")
    ).all()
    for app in new_apps:
        _auto_describe(app)
    db.commit()
    logger.info(f"Chocolatey: {n} Windows apps")
    return n


# ═══ Master daily sync ═══════════════════════════════════════════════════════

async def run_daily_sync(db: Session, limit_per_os: int = DAILY_LIMIT_PER_OS) -> dict:
    """
    Master pipeline: scrape 50 apps per OS, auto-generate descriptions.
    Returns stats dict with count per platform.
    """
    logger.info(f"=== APKDroid Daily Sync Starting (limit={limit_per_os}/OS) ===")
    results = {}

    try:
        results["android"] = await sync_fdroid_apps(db, limit=limit_per_os)
    except Exception as e:
        logger.error(f"F-Droid sync failed: {e}")
        results["android"] = 0

    try:
        snap_n = await sync_snap_apps(db, limit=limit_per_os // 2)
        flat_n = await sync_flathub_apps(db, limit=limit_per_os // 2)
        results["linux"] = snap_n + flat_n
    except Exception as e:
        logger.error(f"Linux sync failed: {e}")
        results["linux"] = 0

    try:
        results["macos"] = await sync_homebrew_apps(db, limit=limit_per_os)
    except Exception as e:
        logger.error(f"Homebrew sync failed: {e}")
        results["macos"] = 0

    try:
        results["windows"] = await sync_chocolatey_apps(db, limit=limit_per_os)
    except Exception as e:
        logger.error(f"Chocolatey sync failed: {e}")
        results["windows"] = 0

    # Final backfill: catch any apps still missing descriptions
    try:
        missing = db.query(App).filter(
            (App.description == None) | (App.description == "")
        ).all()
        for app in missing:
            _auto_describe(app)
        if missing:
            db.commit()
            logger.info(f"Description backfill: {len(missing)} apps")
        results["descriptions_filled"] = len(missing)
    except Exception as e:
        logger.error(f"Description backfill failed: {e}")

    # Update category counts
    try:
        categories = db.query(Category).all()
        for cat in categories:
            cat.app_count = db.query(App).filter(App.category_id == cat.id).count()
        db.commit()
    except Exception as e:
        logger.error(f"Failed to update category counts: {e}")

    total = sum(v for k, v in results.items() if k != "descriptions_filled")
    logger.info(f"=== Daily Sync Complete: {total} total apps | {results} ===")
    return results


# Legacy alias — used by old scheduler
async def scheduled_app_sync(db: Session):
    await run_daily_sync(db)


# ─── Sync provider class (used by admin.py) ──────────────────────────────────

class LegalAppDataProvider:
    async def sync_fdroid_apps(self, db, limit=50): return await sync_fdroid_apps(db, limit)
    async def sync_snap_apps(self, db, limit=50): return await sync_snap_apps(db, limit)
    async def sync_flathub_apps(self, db, limit=50): return await sync_flathub_apps(db, limit)
    async def sync_homebrew_apps(self, db, limit=50): return await sync_homebrew_apps(db, limit)
