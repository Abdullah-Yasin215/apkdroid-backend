from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Category, App
from app.schemas.app import CategoryResponse, AppResponse

router = APIRouter(tags=["categories"])


@router.get("/api/v1/categories", response_model=list)
async def list_categories(db: Session = Depends(get_db)):
    """Get all categories"""
    categories = db.query(Category).all()
    return [CategoryResponse.from_orm(cat) for cat in categories]


@router.get("/api/v1/categories/{slug}", response_model=dict)
async def get_category_apps(
    slug: str,
    page: int = Query(1, ge=1),
    limit: int = Query(24, ge=1, le=100),
    sort: str = Query("rating", regex="^(rating|newest)$"),
    db: Session = Depends(get_db)
):
    """Get apps in a specific category"""
    category = db.query(Category).filter_by(slug=slug).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    skip = (page - 1) * limit
    
    query = db.query(App).filter(
        App.category_id == category.id,
        App.status == "active"
    )
    
    if sort == "rating":
        query = query.order_by(desc(App.rating))
    else:
        query = query.order_by(desc(App.created_at))
    
    total = query.count()
    apps = query.offset(skip).limit(limit).all()
    
    return {
        "category": CategoryResponse.from_orm(category),
        "apps": [AppResponse.from_orm(app) for app in apps],
        "total": total,
        "page": page,
        "limit": limit
    }
