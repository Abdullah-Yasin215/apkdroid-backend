#!/usr/bin/env python3
"""Initialize database tables"""

import sys
from app.database import Base, engine
from app.models import App, APKVersion, Category, Download, DownloadLog, VirusScan, AppReview

def init_db():
    """Create all tables"""
    try:
        print("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = init_db()
    sys.exit(0 if success else 1)
