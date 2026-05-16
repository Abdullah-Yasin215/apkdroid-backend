from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, Float, ForeignKey, ARRAY, Numeric, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class App(Base):
    """Core app/software model supporting both Android APKs and PC software"""
    __tablename__ = "apps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    package_id = Column(String(200), unique=True, nullable=False)  # com.example.app or windows_app_id
    slug = Column(String(220), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    developer = Column(String(200))
    developer_id = Column(String(200))
    category_id = Column(UUID(as_uuid=True), ForeignKey("categories.id"))
    
    # NEW: Software type (android, windows, mac, linux)
    software_type = Column(String(20), default="android", nullable=False)
    
    # Branding/Images
    icon_url = Column(Text)
    header_image = Column(Text)
    
    # Content
    short_desc = Column(Text)
    description = Column(Text)
    detailed_description = Column(Text)  # NEW: Original content for SEO
    installation_guide = Column(Text)    # NEW: How to install/setup
    faq = Column(Text)                   # NEW: FAQ content
    
    # Ratings & Reviews (aggregated from user_reviews)
    rating = Column(Numeric(3, 2), default=0.0)
    rating_count = Column(Integer, default=0)
    downloads_range = Column(String(30))
    
    # Version Info
    size = Column(String(20))
    latest_version = Column(String(50))
    min_android = Column(String(20))     # For Android apps
    min_os_version = Column(String(50))  # For PC software (e.g., "Windows 10", "macOS 10.15")
    
    # Store Info
    content_rating = Column(String(30))
    is_free = Column(Boolean, default=True)
    price = Column(Numeric(8, 2), default=0.0)
    
    # Media
    screenshots = Column(ARRAY(Text))
    tags = Column(ARRAY(String(50)))
    permissions = Column(ARRAY(Text))    # Android permissions
    system_requirements = Column(ARRAY(Text))  # PC system requirements
    
    # URLs & Legal
    play_store_url = Column(Text)        # For Android
    official_website = Column(Text)      # For PC software
    privacy_policy = Column(Text)
    whats_new = Column(Text)
    
    # Features
    is_featured = Column(Boolean, default=False)
    is_editor_pick = Column(Boolean, default=False)
    status = Column(String(20), default="active")
    
    # NEW: Data source info for legal compliance
    data_source = Column(String(50), default="google_play")  # google_play, apkpure, open_source, official_website
    attribution = Column(Text)  # Attribution text for legal compliance
    
    # Metadata
    scraped_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    versions = relationship("APKVersion", back_populates="app", cascade="all, delete-orphan")
    downloads = relationship("Download", back_populates="app", cascade="all, delete-orphan")
    reviews = relationship("AppReview", back_populates="app", cascade="all, delete-orphan")
    scans = relationship("VirusScan", back_populates="app", cascade="all, delete-orphan")


class APKVersion(Base):
    """App version with download link and security information"""
    __tablename__ = "apk_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"))
    version_name = Column(String(50), nullable=False)
    version_code = Column(Integer)
    
    # NEW: Real download link (affiliate, redirect, or mirror)
    download_url = Column(Text)          # Actual download link
    download_source = Column(String(50)) # apkpure, apkmirror, official, affiliate
    affiliate_url = Column(Text)         # For monetization if available
    
    # File Info
    file_size = Column(String(20))
    file_size_bytes = Column(Integer)    # For sorting/filtering
    md5_hash = Column(String(32))        # NEW: MD5 checksum
    sha256 = Column(String(64))
    
    # Platform Info
    min_android = Column(String(20))
    target_sdk = Column(Integer)
    arch = Column(String(20), default="universal")  # arm64-v8a, armeabi-v7a, x86, x86_64
    
    # Version Details
    changelog = Column(Text)
    release_date = Column(DateTime)
    
    # Security & Trust (from VirusTotal)
    security_scan_status = Column(String(20))  # pending, safe, suspicious, malware
    security_scan_date = Column(DateTime)
    security_warnings_count = Column(Integer, default=0)
    
    # Stats
    download_count = Column(Integer, default=0)
    is_latest = Column(Boolean, default=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    app = relationship("App", back_populates="versions")


class Download(Base):
    """Track downloads for analytics and legal compliance"""
    __tablename__ = "downloads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("apk_versions.id", ondelete="SET NULL"))
    
    # User/Device Info (anonymized)
    ip_hash = Column(String(64))
    country = Column(String(3))
    user_agent = Column(Text)
    referrer = Column(Text)
    
    # Download Info
    download_status = Column(String(20), default="completed")  # pending, completed, failed
    file_size_bytes = Column(Integer)
    
    logged_at = Column(DateTime, default=datetime.utcnow)
    
    app = relationship("App", back_populates="downloads")


class AppReview(Base):
    """User reviews and ratings for content depth"""
    __tablename__ = "app_reviews"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"))
    
    user_name = Column(String(100))
    rating = Column(Numeric(2, 1), nullable=False)  # 1-5 stars
    title = Column(String(200))
    content = Column(Text)
    helpful_count = Column(Integer, default=0)
    
    # Review source
    source = Column(String(50), default="user")  # user, play_store, app_store
    source_id = Column(String(200))  # Original review ID from source
    
    status = Column(String(20), default="approved")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    app = relationship("App", back_populates="reviews")


class VirusScan(Base):
    """VirusTotal scan results for trust/safety signals"""
    __tablename__ = "virus_scans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id", ondelete="CASCADE"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("apk_versions.id", ondelete="SET NULL"))
    
    # File Info
    file_hash = Column(String(64), nullable=False)  # SHA256
    file_size = Column(Integer)
    
    # VirusTotal Data
    vt_scan_id = Column(String(200))
    vt_permalink = Column(Text)
    
    # Results
    malicious_count = Column(Integer, default=0)
    suspicious_count = Column(Integer, default=0)
    undetected_count = Column(Integer, default=0)
    total_vendors = Column(Integer, default=0)
    
    # Detailed Results
    vendor_results = Column(JSON)  # Store vendor-by-vendor results
    
    # Trust Badge
    safety_badge = Column(String(20), default="unknown")  # safe, suspicious, malware, unknown
    
    scan_date = Column(DateTime)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    app = relationship("App", back_populates="scans")
