"""
Winget (Windows Package Manager) scraper for APKDroid.
Fetches Windows software metadata from winget.run API.
Phase 4 — Windows software support.
"""

import httpx
import logging
from sqlalchemy.orm import Session
from app.models import App, Category
import uuid

logger = logging.getLogger(__name__)

WINGET_API_BASE = "https://winget.run/api/v2/packages"


def _get_or_create_windows_category(db: Session) -> Category:
    """Ensure a 'Windows Software' category exists."""
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


def _build_slug(name: str, pkg_id: str) -> str:
    """Generate a URL-safe slug from app name + package id suffix."""
    try:
        from slugify import slugify  # python-slugify
        base = slugify(name)[:100]
        suffix = slugify(pkg_id.split(".")[-1])[:30] if "." in pkg_id else pkg_id[:20]
        return f"{base}-{suffix}" if base else f"winget-{suffix}"
    except Exception:
        # fallback without python-slugify
        safe = "".join(c if c.isalnum() else "-" for c in (name + "-" + pkg_id).lower())
        return safe[:130].strip("-")


async def sync_winget_apps(db: Session, limit: int = 500) -> int:
    """
    Fetch Windows packages from winget.run and upsert into the database.
    Returns the number of apps added/updated.
    """
    category = _get_or_create_windows_category(db)
    count = 0
    page = 1
    page_size = min(limit, 100)

    async with httpx.AsyncClient(timeout=30.0) as client:
        while count < limit:
            try:
                resp = await client.get(
                    WINGET_API_BASE,
                    params={"take": page_size, "skip": (page - 1) * page_size},
                )
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.warning(f"Winget API error (page {page}): {e}")
                break

            packages = data.get("Packages", data) if isinstance(data, dict) else data
            if not packages:
                break

            for pkg in packages:
                if count >= limit:
                    break
                try:
                    pkg_id = pkg.get("Id") or pkg.get("PackageIdentifier", "")
                    if not pkg_id:
                        continue

                    name = pkg.get("Name") or pkg.get("PackageName") or pkg_id
                    publisher = pkg.get("Publisher") or pkg.get("Author") or ""
                    latest = pkg.get("Latest") or pkg.get("Versions", [{}])
                    if isinstance(latest, list):
                        latest = latest[0] if latest else {}
                    version = latest.get("Version", "") if isinstance(latest, dict) else str(latest)
                    icon_url = pkg.get("IconUrl") or ""
                    homepage = pkg.get("Homepage") or ""
                    description = pkg.get("Description") or pkg.get("ShortDescription") or ""

                    slug = _build_slug(name, pkg_id)

                    # Check for slug collision and deduplicate
                    existing_slug = db.query(App).filter(App.slug == slug).first()
                    if existing_slug and existing_slug.package_id != pkg_id:
                        slug = f"{slug}-win"

                    existing = db.query(App).filter(App.package_id == pkg_id).first()
                    if existing:
                        # Update existing record
                        existing.name = name
                        existing.developer = publisher
                        existing.latest_version = version
                        existing.icon_url = icon_url or existing.icon_url
                        existing.description = description or existing.description
                        existing.official_website = homepage or existing.official_website
                        existing.data_source = "winget"
                        existing.software_type = "windows"
                        existing.status = "active"
                    else:
                        app = App(
                            id=uuid.uuid4(),
                            package_id=pkg_id,
                            slug=slug,
                            name=name,
                            developer=publisher,
                            latest_version=version,
                            icon_url=icon_url or None,
                            short_desc=description[:255] if description else None,
                            description=description,
                            official_website=homepage or None,
                            software_type="windows",
                            is_free=True,
                            data_source="winget",
                            status="active",
                            category_id=category.id,
                        )
                        db.add(app)

                    count += 1

                except Exception as e:
                    logger.warning(f"Skipping winget package {pkg.get('Id', '?')}: {e}")
                    continue

            try:
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"DB commit failed after winget page {page}: {e}")

            if len(packages) < page_size:
                break  # no more pages

            page += 1

    logger.info(f"Winget scrape complete: {count} apps processed.")
    return count
