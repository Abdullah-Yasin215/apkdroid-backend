import asyncio
import time
from datetime import datetime
from sqlalchemy.orm import Session
from google_play_scraper import app as play_app, collection
from app.models import App, Category
from app.utils.slug import slugify


CATEGORIES = {
    'GAME_ACTION': 'Action Games',
    'GAME_ADVENTURE': 'Adventure Games',
    'GAME_PUZZLE': 'Puzzle Games',
    'GAME_RACING': 'Racing Games',
    'COMMUNICATION': 'Communication',
    'SOCIAL': 'Social',
    'TOOLS': 'Tools',
    'PHOTOGRAPHY': 'Photography',
    'PRODUCTIVITY': 'Productivity',
    'ENTERTAINMENT': 'Entertainment',
    'EDUCATION': 'Education',
    'FINANCE': 'Finance',
    'HEALTH_AND_FITNESS': 'Health & Fitness',
    'MAPS_AND_NAVIGATION': 'Maps & Navigation',
    'MUSIC_AND_AUDIO': 'Music & Audio',
    'NEWS_AND_MAGAZINES': 'News & Magazines',
    'SHOPPING': 'Shopping',
    'TRAVEL_AND_LOCAL': 'Travel & Local',
    'VIDEO_PLAYERS': 'Video Players',
    'WEATHER': 'Weather'
}


async def ensure_categories(db: Session):
    """Ensure all categories exist in database"""
    for cat_key, cat_name in CATEGORIES.items():
        existing = db.query(Category).filter_by(slug=cat_key.lower()).first()
        if not existing:
            category = Category(
                name=cat_name,
                slug=cat_key.lower(),
                icon="📱",
                description=f"Browse {cat_name} for Android"
            )
            db.add(category)
    db.commit()


async def scrape_category(cat_key: str, cat_name: str, db: Session, apps_limit: int = 200):
    """Scrape apps from a single category"""
    try:
        results = collection.Collection(category=cat_key, count=apps_limit)
        apps_list = results.fetch()
        
        for app_data in apps_list:
            try:
                await asyncio.sleep(0.3)  # Rate limit
                
                details = play_app(app_data['appId'], lang='en', country='us')
                await upsert_app(details, cat_key, db)
                
            except Exception as e:
                print(f"Error scraping app {app_data.get('appId')}: {e}")
                continue
    except Exception as e:
        print(f"Error scraping category {cat_key}: {e}")


async def upsert_app(details: dict, category_key: str, db: Session):
    """Insert or update app in database"""
    try:
        existing = db.query(App).filter_by(package_id=details.get('appId')).first()
        
        app_slug = slugify(details.get('title', ''))
        
        category = db.query(Category).filter_by(slug=category_key.lower()).first()
        category_id = category.id if category else None
        
        data = {
            'package_id': details.get('appId'),
            'slug': app_slug,
            'name': details.get('title', ''),
            'developer': details.get('developer', ''),
            'developer_id': details.get('developerId'),
            'category_id': category_id,
            'icon_url': details.get('icon'),
            'header_image': details.get('headerImage'),
            'short_desc': details.get('summary', ''),
            'description': details.get('description', ''),
            'rating': float(details.get('score', 0)),
            'rating_count': details.get('ratings', 0),
            'downloads_range': details.get('installs', ''),
            'size': details.get('size', ''),
            'latest_version': details.get('version', ''),
            'min_android': details.get('androidVersion', ''),
            'content_rating': details.get('contentRating', ''),
            'is_free': details.get('free', True),
            'price': float(details.get('price', 0)),
            'screenshots': details.get('screenshots', []),
            'tags': [cat for cat in details.get('genreId', '').split(',') if cat],
            'permissions': details.get('permissions', []),
            'play_store_url': f"https://play.google.com/store/apps/details?id={details.get('appId')}",
            'privacy_policy': details.get('privacyPolicy'),
            'whats_new': details.get('recentChanges', ''),
            'scraped_at': datetime.utcnow()
        }
        
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            app = App(**data)
            db.add(app)
        
        db.commit()
    except Exception as e:
        print(f"Error upserting app: {e}")
        db.rollback()


async def run_scraper(db: Session, apps_per_category: int = 100):
    """Run full scraper for all categories"""
    print("Starting scraper...")
    await ensure_categories(db)
    
    tasks = []
    for cat_key, cat_name in CATEGORIES.items():
        tasks.append(scrape_category(cat_key, cat_name, db, apps_per_category))
    
    await asyncio.gather(*tasks)
    print("Scraper finished!")
