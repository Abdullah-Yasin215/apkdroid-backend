from pydantic import BaseModel, field_validator
from typing import Optional, List
from decimal import Decimal
from uuid import UUID


class CategoryBase(BaseModel):
    name: str
    slug: str
    icon: Optional[str] = None
    description: Optional[str] = None
    color: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: str
    app_count: int

    class Config:
        from_attributes = True

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class APKVersionResponse(BaseModel):
    id: str
    version_name: str
    version_code: Optional[int] = None
    file_size: Optional[str] = None
    min_android: Optional[str] = None
    changelog: Optional[str] = None
    download_count: int
    is_latest: bool
    release_date: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator('id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class AppBase(BaseModel):
    package_id: str
    name: str
    developer: Optional[str] = None
    short_desc: Optional[str] = None
    description: Optional[str] = None


class AppResponse(AppBase):
    id: str
    slug: str
    icon_url: Optional[str] = None
    rating: Optional[float] = None
    rating_count: int
    downloads_range: Optional[str] = None
    size: Optional[str] = None
    latest_version: Optional[str] = None
    is_free: bool
    price: Optional[float] = None
    category_id: Optional[str] = None
    software_type: str

    class Config:
        from_attributes = True

    @field_validator('id', 'category_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class AppDetailResponse(AppResponse):
    header_image: Optional[str] = None
    min_android: Optional[str] = None
    content_rating: Optional[str] = None
    screenshots: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    play_store_url: Optional[str] = None
    privacy_policy: Optional[str] = None
    whats_new: Optional[str] = None
    is_featured: bool
    is_editor_pick: bool
    versions: Optional[List[APKVersionResponse]] = None


class SearchResponse(BaseModel):
    results: List[AppResponse]
    query: str
    count: int


class InitiateDownloadResponse(BaseModel):
    """Response for download link initiation."""
    download_id: str
    redirect_url: str
    countdown_seconds: int
    source: Optional[str] = "official"
    actual_file_url: str

    class Config:
        from_attributes = True

    @field_validator('download_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v


class DownloadResponse(BaseModel):
    """Response for download tracking and status."""
    id: str
    app_id: str
    version_id: Optional[str] = None
    app_name: str
    version_name: Optional[str] = None
    file_size_bytes: Optional[int] = None
    download_source: Optional[str] = "official"
    download_url: str
    status: str = "pending"  # pending, in_progress, completed, failed
    downloaded_at: Optional[str] = None
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None

    class Config:
        from_attributes = True

    @field_validator('id', 'app_id', 'version_id', mode='before')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        return v
