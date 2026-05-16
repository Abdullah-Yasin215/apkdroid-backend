from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from app.database import Base


class DownloadLog(Base):
    __tablename__ = "download_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    app_id = Column(UUID(as_uuid=True), ForeignKey("apps.id"))
    version_id = Column(UUID(as_uuid=True), ForeignKey("apk_versions.id"))
    ip_hash = Column(String(64))
    country = Column(String(3))
    user_agent = Column(Text)
    referrer = Column(Text)
    logged_at = Column(DateTime, default=datetime.utcnow)
