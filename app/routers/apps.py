from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_
from app.database import get_db
from app.models import App, APKVersion, Download  # BUG 1 FIX: DownloadLog does not exist
from app.schemas.app import AppResponse, AppDetailResponse, SearchResponse, APKVersionResponse
from app.services.cache import cache_get, cache_set
from app.utils.pagination import paginate

router = APIRouter(tags=["apps"])


@router.get("/api/v1/apps", response_model=dict)
async def list_apps(
    category: str = Query(None),
    platform: str = Query(None, regex="^(android|windows|macos|linux)$"),  # Phase 3: platform filter
    sort: str = Query("rating", regex="^(rating|newest|downloads)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all apps with filters and pagination"""
    skip = (page - 1) * limit
    skip, limit = paginate(skip=skip, limit=limit)
    
    query = db.query(App).filter(App.status == "active")
    
    if category:
        query = query.filter(App.category_id == category)
    
    if platform:
        query = query.filter(App.software_type == platform)
    
    if sort == "rating":
        query = query.order_by(desc(App.rating))
    elif sort == "newest":
        query = query.order_by(desc(App.created_at))
    elif sort == "downloads":
        # Sort by rating_count as proxy for downloads
        query = query.order_by(desc(App.rating_count))
    
    total = query.count()
    apps = query.offset(skip).limit(limit).all()
    
    return {
        "items": [AppResponse.model_validate(app) for app in apps],
        "total": total,
        "page": page,
        "limit": limit
    }


@router.get("/api/v1/apps/featured", response_model=dict)
async def featured_apps(
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get featured/editor pick apps"""
    cache_key = f"featured_apps_{limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    apps = db.query(App).filter(
        and_(App.is_featured == True, App.status == "active")
    ).order_by(desc(App.rating)).limit(limit).all()
    
    result = {"items": [AppResponse.model_validate(app) for app in apps]}
    cache_set(cache_key, result, ttl=3600)
    return result


@router.get("/api/v1/apps/new", response_model=dict)
async def new_apps(
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get recently added apps"""
    cache_key = f"new_apps_{limit}"
    cached = cache_get(cache_key)
    if cached:
        return cached
    
    apps = db.query(App).filter(
        App.status == "active"
    ).order_by(desc(App.created_at)).limit(limit).all()
    
    result = {"items": [AppResponse.model_validate(app) for app in apps]}
    cache_set(cache_key, result, ttl=1800)
    return result


@router.get("/api/v1/apps/search", response_model=SearchResponse)
async def search_apps(
    q: str = Query(..., min_length=2, max_length=100),
    platform: str = Query(None, regex="^(android|windows|macos|linux)$"),
    category: str = Query(None),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Full-text search for apps by name or developer"""
    cache_key = f"search_{q}_{platform}_{category}_{limit}"
    cached = cache_get(cache_key)
    if cached:
        return SearchResponse(**cached)
    
    # Search in name and developer fields
    search_term = f"%{q.lower()}%"
    filters = [
        App.status == "active",
        func.lower(App.name).ilike(search_term) | func.lower(App.developer).ilike(search_term)
    ]
    if platform:
        filters.append(App.software_type == platform)
    if category:
        filters.append(App.category_id == category)
    
    apps = db.query(App).filter(and_(*filters)).order_by(desc(App.rating)).limit(limit).all()
    
    result = {
        "results": [AppResponse.model_validate(app) for app in apps],
        "query": q,
        "count": len(apps)
    }
    cache_set(cache_key, result, ttl=3600)
    return result


@router.get("/api/v1/apps/{slug}", response_model=AppDetailResponse)
async def get_app_detail(
    slug: str,
    db: Session = Depends(get_db)
):
    """Get detailed app information by slug (SEO-friendly URL)"""
    cache_key = f"app_detail_{slug}"
    
    # BUG 6 + URL slug fix: route by slug for SEO-friendly URLs
    app = db.query(App).filter(
        (App.slug == slug) | (App.package_id == slug)
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    versions = db.query(APKVersion).filter(
        APKVersion.app_id == app.id
    ).order_by(desc(APKVersion.uploaded_at)).limit(10).all()
    
    # BUG 6 FIX: Build the dict manually — Pydantic v2 model instances are immutable
    app_data = {
        **{c.name: getattr(app, c.name) for c in app.__table__.columns},
        "versions": [APKVersionResponse.model_validate(v) for v in versions]
    }
    return AppDetailResponse.model_validate(app_data)


@router.get("/api/v1/apps/{slug}/similar", response_model=dict)
async def similar_apps(
    slug: str,
    limit: int = Query(6, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get similar apps from the same category"""
    app = db.query(App).filter(
        (App.slug == slug) | (App.package_id == slug)
    ).first()
    if not app:
        raise HTTPException(status_code=404, detail="App not found")
    
    if not app.category_id:
        return {"apps": []}
    
    similar = db.query(App).filter(
        and_(
            App.category_id == app.category_id,
            App.id != app.id,
            App.status == "active"
        )
    ).order_by(desc(App.rating)).limit(limit).all()
    
    # BUG 2 FIX: Use model_validate() instead of deprecated from_orm()
    return {"apps": [AppResponse.model_validate(a) for a in similar]}
