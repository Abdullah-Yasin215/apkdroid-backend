from fastapi import APIRouter
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import SessionLocal
from app.models import App
import math
from datetime import datetime

router = APIRouter(tags=["sitemap"])


@router.get("/sitemap.xml")
async def sitemap_index():
    """Generate sitemap index file"""
    db = SessionLocal()
    try:
        total = db.query(App).count()
        chunks = math.ceil(total / 50000)
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        for i in range(chunks):
            xml += f'  <sitemap>\n'
            xml += f'    <loc>https://apkdroid.net/sitemap-{i}.xml</loc>\n'
            xml += f'    <lastmod>{datetime.now().date()}</lastmod>\n'
            xml += f'  </sitemap>\n'
        
        xml += '</sitemapindex>'
        
        return Response(xml, media_type="application/xml")
    finally:
        db.close()


@router.get("/sitemap-{chunk}.xml")
async def sitemap_chunk(chunk: int):
    """Generate individual sitemap chunk"""
    db = SessionLocal()
    try:
        apps = db.query(App).order_by(desc(App.updated_at)).offset(
            chunk * 50000
        ).limit(50000).all()
        
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Add static pages
        if chunk == 0:
            static_urls = [
                ("https://apkdroid.net/", "weekly", "1.0"),
                ("https://apkdroid.net/privacy", "yearly", "0.5"),
                ("https://apkdroid.net/terms", "yearly", "0.5"),
                ("https://apkdroid.net/dmca", "yearly", "0.5"),
            ]
            for loc, freq, priority in static_urls:
                xml += f'  <url>\n'
                xml += f'    <loc>{loc}</loc>\n'
                xml += f'    <lastmod>{datetime.now().date()}</lastmod>\n'
                xml += f'    <changefreq>{freq}</changefreq>\n'
                xml += f'    <priority>{priority}</priority>\n'
                xml += f'  </url>\n'
        
        # Add app pages
        for app in apps:
            xml += f'  <url>\n'
            xml += f'    <loc>https://apkdroid.net/app/{app.slug}</loc>\n'
            xml += f'    <lastmod>{app.updated_at.date()}</lastmod>\n'
            xml += f'    <changefreq>weekly</changefreq>\n'
            xml += f'    <priority>0.8</priority>\n'
            xml += f'  </url>\n'
        
        xml += '</urlset>'
        
        return Response(xml, media_type="application/xml")
    finally:
        db.close()
