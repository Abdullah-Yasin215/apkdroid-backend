from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List
from pydantic import field_validator
import json


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_url: str = "postgresql://user:password@localhost/apkdroid"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # App
    secret_key: str = "your-secret-key-change-this"
    admin_api_key: str = "change-this-admin-key-in-env"  # BUG 3: required for admin auth
    app_name: str = "APKDroid"
    app_version: str = "1.0.0"
    allowed_origins: List[str] = ["https://apkdroid.net", "http://localhost:3000"]
    
    # Scraper
    scraper_delay: float = 0.3
    apps_per_scrape_run: int = 10000
    
    # VirusTotal Integration
    virustotal_api_key: str = ""  # Set via environment variable
    enable_virus_scanning: bool = True
    
    # Download Sources
    enable_affiliate_links: bool = True
    preferred_download_sources: List[str] = ["f_droid", "apkmirror", "apkpure"]
    
    # Download Redirect (for tracking and countdown page)
    enable_download_redirect: bool = True
    download_redirect_timeout_seconds: int = 5  # Countdown timer
    
    # Content Settings
    enable_user_reviews: bool = True
    max_reviews_per_app: int = 100
    
    # SEO
    site_url: str = "https://apkdroid.net"
    robots_txt_path: str = "/robots.txt"
    sitemap_chunk_size: int = 50000  # Max URLs per sitemap per Google spec
    
    # API Settings
    api_title: str = "APKDroid API"
    api_description: str = "Complete APK and PC software download directory"
    
    # Google AdSense
    google_adsense_publisher_id: str = ""
    
    # Email/SMTP
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    admin_email: str = "admin@apkdroid.net"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
