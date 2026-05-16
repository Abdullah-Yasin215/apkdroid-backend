#!/usr/bin/env python3
"""Reset database: drop all tables and recreate with sample data"""

import sys
import os

sys.path.insert(0, '/Users/abdullahyasin/Desktop/FreeLancingProject/apkdroid-backend')

from app.database import Base, engine, SessionLocal
from app.models import App, Category
import uuid

def reset_db():
    """Drop all tables, recreate them, and add sample data"""
    try:
        print("Dropping all existing tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ Tables dropped!")
        
        print("\nCreating fresh database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Tables created!")
        
        print("\nAdding sample data...")
        db = SessionLocal()
        
        # Create a category
        cat = Category(
            id=str(uuid.uuid4()),
            name="Productivity",
            slug="productivity",
            icon="📱"
        )
        db.add(cat)
        db.flush()
        
        # Create sample apps
        apps_data = [
            {
                "package_id": "org.mozilla.firefox",
                "slug": "mozilla-firefox",
                "name": "Mozilla Firefox",
                "developer": "Mozilla",
                "short_desc": "Fast, private browser",
                "description": "A free and open-source web browser",
                "icon_url": "https://f-droid.org/icons-640/org.mozilla.firefox.12201.png",
                "rating": 4.5,
                "rating_count": 10000,
            },
            {
                "package_id": "org.videolan.vlc",
                "slug": "vlc-media-player",
                "name": "VLC Media Player",
                "developer": "VideoLAN",
                "short_desc": "Universal media player",
                "description": "Play any video and audio file",
                "icon_url": "https://f-droid.org/icons-640/org.videolan.vlc.12201.png",
                "rating": 4.7,
                "rating_count": 8500,
            },
            {
                "package_id": "org.telegram.messenger",
                "slug": "telegram",
                "name": "Telegram",
                "developer": "Telegram",
                "short_desc": "Fast messaging app",
                "description": "Secure messaging and voice calls",
                "icon_url": "https://f-droid.org/icons-640/org.telegram.messenger.12201.png",
                "rating": 4.6,
                "rating_count": 12000,
            },
        ]
        
        for app_data in apps_data:
            app = App(
                id=str(uuid.uuid4()),
                package_id=app_data["package_id"],
                slug=app_data["slug"],
                name=app_data["name"],
                developer=app_data["developer"],
                short_desc=app_data["short_desc"],
                description=app_data["description"],
                software_type="android",
                icon_url=app_data["icon_url"],
                rating=app_data["rating"],
                rating_count=app_data["rating_count"],
                is_free=True,
                status="active",
                category_id=cat.id
            )
            db.add(app)
        
        db.commit()
        print(f"✅ Added {len(apps_data)} sample apps!")
        db.close()
        
        print("\n✅ Database reset complete!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = reset_db()
    sys.exit(0 if success else 1)
