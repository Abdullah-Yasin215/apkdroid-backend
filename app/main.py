from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from contextlib import asynccontextmanager
from app.database import Base, engine
from app.config import get_settings
from app.routers import apps, categories, download, sitemap, pages, admin
from app.scheduler import start_scheduler
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create tables on startup
Base.metadata.create_all(bind=engine)

settings = get_settings()

# Background scheduler
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global scheduler
    logger.info("APKDroid API Starting...")
    
    # Start background scheduler for legal app data sync
    scheduler = start_scheduler()
    
    yield
    
    # Shutdown
    if scheduler:
        scheduler.shutdown()
    logger.info("APKDroid API Shutting down...")


app = FastAPI(
    title="APKDroid API",
    version="1.0.0",
    description="Complete APK & PC software download directory (Legal & Safe)",
    lifespan=lifespan
)

# Middleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(apps.router)
app.include_router(categories.router)
app.include_router(download.router)
app.include_router(sitemap.router)
app.include_router(pages.router)
app.include_router(admin.router)


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "APKDroid API is running",
        "scheduler": "active" if scheduler and scheduler.running else "inactive"
    }
