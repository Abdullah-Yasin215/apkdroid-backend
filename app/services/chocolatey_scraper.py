"""
Windows app scraper using Chocolatey community repository (OData/Atom XML).
Uses full namespace URIs to avoid alias-resolution issues with ElementTree.
Rate-limited, polite, with user-agent rotation.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import App, Category
import aiohttp
import random
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

CHOCO_API = "https://community.chocolatey.org/api/v2/Packages"

# Full namespace URIs (ElementTree requires these, not prefix aliases)
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_D    = "http://schemas.microsoft.com/ado/2007/08/dataservices"
NS_M    = "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata"

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
]


def _get_or_create_category(db: Session) -> Category:
    cat = db.query(Category).filter(Category.slug == "windows-software").first()
    if not cat:
        cat = Category(
            id=uuid.uuid4(),
            name="Windows Software",
            slug="windows-software",
            description="Applications for Microsoft Windows",
            icon="🪟",
        )
        db.add(cat)
        db.flush()
    return cat


def _slug_from(name: str, pkg_id: str) -> str:
    try:
        from slugify import slugify
        base = slugify(name)[:80]
        suffix = slugify(pkg_id)[:30]
        s = f"{base}-{suffix}" if base else f"win-{suffix}"
        return s or f"win-{uuid.uuid4().hex[:8]}"
    except Exception:
        safe = "".join(c if c.isalnum() else "-" for c in (name + "-" + pkg_id).lower())
        return safe[:110].strip("-") or f"win-{uuid.uuid4().hex[:8]}"


def _prop(props: ET.Element, tag: str) -> str:
    """Get text of a d:Tag property element using full namespace URI."""
    el = props.find(f"{{{NS_D}}}{tag}")
    return (el.text or "").strip() if el is not None else ""


def _parse_entry(entry: ET.Element) -> dict | None:
    """Parse one Atom <entry> into an app dict."""
    try:
        # m:properties is a direct child of entry
        props = entry.find(f"{{{NS_M}}}properties")
        if props is None:
            return None

        # Package ID comes from the entry <id> URL or d:Id inside the Packages(Id='...'...) href
        # Actually ID is in entry > id element text like: .../Packages(Id='foo', Version='1.0')
        entry_id_el = entry.find(f"{{{NS_ATOM}}}id")
        pkg_id = ""
        if entry_id_el is not None and entry_id_el.text:
            # Extract Id from: http://.../Packages(Id='firefox',Version='120.0')
            raw = entry_id_el.text
            if "Id='" in raw:
                pkg_id = raw.split("Id='")[1].split("'")[0]

        if not pkg_id:
            return None

        title_el = entry.find(f"{{{NS_ATOM}}}title")
        summary_el = entry.find(f"{{{NS_ATOM}}}summary")
        author_el = entry.find(f"{{{NS_ATOM}}}author/{{{NS_ATOM}}}name")

        title_d = _prop(props, "Title")
        name = title_d or (title_el.text if title_el is not None else "") or pkg_id
        summary = (summary_el.text if summary_el is not None else "") or ""
        description = _prop(props, "Description")
        version = _prop(props, "Version")
        icon_url = _prop(props, "IconUrl")
        homepage = _prop(props, "ProjectUrl") or _prop(props, "GalleryDetailsUrl")
        developer = (author_el.text if author_el is not None else "").strip()
        download_count = _prop(props, "DownloadCount")

        return {
            "package_id": pkg_id,
            "name": name.strip() or pkg_id,
            "short_desc": (summary[:255] or description[:255]) if (summary or description) else None,
            "description": description or None,
            "latest_version": version,
            "icon_url": icon_url or None,
            "official_website": homepage or None,
            "developer": developer,
            "downloads_range": download_count or None,
        }
    except Exception as e:
        logger.debug(f"Parse error: {e}")
        return None


async def sync_chocolatey_apps(db: Session, limit: int = 100) -> int:
    """
    Fetch Windows packages from Chocolatey (OData/Atom XML).
    Paginates with $skip. Returns apps added/updated count.
    """
    category = _get_or_create_category(db)
    count = 0
    page_size = min(50, limit)
    skip = random.randint(0, 2000)

    async with aiohttp.ClientSession() as session:
        while count < limit:
            # Build URL manually — aiohttp encodes '$' -> '%24' breaking OData
            qs = f"$filter=IsLatestVersion+eq+true&$top={page_size}&$skip={skip}"
            url = f"{CHOCO_API}?{qs}"

            try:
                headers = {"User-Agent": random.choice(USER_AGENTS)}
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 429:
                        logger.warning("Chocolatey rate-limited, sleeping 30s")
                        await asyncio.sleep(30)
                        continue
                    if resp.status != 200:
                        logger.warning(f"Chocolatey returned {resp.status} — stopping")
                        break
                    xml_text = await resp.text()
            except Exception as e:
                logger.error(f"Chocolatey request error: {e}")
                break

            try:
                root = ET.fromstring(xml_text)
            except ET.ParseError as e:
                logger.error(f"XML parse error: {e}")
                break

            entries = root.findall(f"{{{NS_ATOM}}}entry")
            if not entries:
                break

            for entry in entries:
                if count >= limit:
                    break
                data = _parse_entry(entry)
                if not data:
                    continue

                pkg_id = data.pop("package_id")
                existing = db.query(App).filter(App.package_id == pkg_id).first()

                if existing:
                    for k, v in data.items():
                        if v and k not in ("id", "slug"):
                            setattr(existing, k, v)
                    existing.software_type = "windows"
                    existing.data_source = "chocolatey"
                    existing.status = "active"
                else:
                    slug = _slug_from(data["name"], pkg_id)
                    if db.query(App).filter(App.slug == slug).first():
                        slug = f"{slug}-{uuid.uuid4().hex[:6]}"

                    new_app = App(
                        id=uuid.uuid4(),
                        package_id=pkg_id,
                        slug=slug,
                        software_type="windows",
                        is_free=True,
                        data_source="chocolatey",
                        status="active",
                        category_id=category.id,
                        scraped_at=datetime.utcnow(),
                        **data,
                    )
                    db.add(new_app)

                count += 1

            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"DB commit failed: {e}")

            await asyncio.sleep(1.2)  # polite rate limit

            if len(entries) < page_size:
                break
            skip += page_size

    logger.info(f"Chocolatey scrape complete: {count} Windows apps")
    return count
