"""
Legal pages and SEO endpoints
Serves privacy policy, terms, DMCA, and other compliance pages
"""

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse, HTMLResponse, JSONResponse
from app.services.legal_templates import LEGAL_PAGES
import markdown
from app.config import get_settings

router = APIRouter(tags=["pages", "legal"])
settings = get_settings()


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Robots.txt for SEO crawlers"""
    return """User-agent: *
Allow: /
Disallow: /api/
Disallow: /*.json$
Disallow: /admin/
Disallow: /dashboard/

# Sitemap location
Sitemap: https://apkdroid.net/sitemap.xml
Sitemap: https://apkdroid.net/sitemap-apps.xml
Sitemap: https://apkdroid.net/sitemap-categories.xml

# Crawl delay (optional)
Crawl-delay: 1

# Request rate limit
Request-rate: 30/1m
"""


@router.get("/ads.txt", response_class=PlainTextResponse)
async def ads_txt():
    """ads.txt for AdSense verification and advertiser transparency"""
    # Replace with your AdSense publisher ID
    return """google.com, ca-pub-XXXXXXXXXXXXXXXX, DIRECT, f08c47fec0942fa0
"""


@router.get("/api/v1/legal/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Privacy Policy - HTML version"""
    md_content = LEGAL_PAGES["privacy"]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Privacy Policy - APKDroid</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ font-size: 32px; margin-bottom: 30px; }}
            h2 {{ font-size: 24px; margin-top: 30px; margin-bottom: 15px; }}
            p {{ margin-bottom: 15px; }}
            strong {{ color: #222; }}
            .last-updated {{ color: #666; font-size: 14px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content)}
    </body>
    </html>
    """
    return html


@router.get("/api/v1/legal/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Terms of Service - HTML version"""
    md_content = LEGAL_PAGES["terms"]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Terms of Service - APKDroid</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ font-size: 32px; margin-bottom: 30px; }}
            h2 {{ font-size: 24px; margin-top: 30px; margin-bottom: 15px; }}
            p {{ margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content)}
    </body>
    </html>
    """
    return html


@router.get("/api/v1/legal/dmca", response_class=HTMLResponse)
async def dmca_policy():
    """DMCA Policy - HTML version"""
    md_content = LEGAL_PAGES["dmca"]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>DMCA Policy - APKDroid</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ font-size: 32px; margin-bottom: 30px; }}
            h2 {{ font-size: 24px; margin-top: 30px; margin-bottom: 15px; }}
            .notice {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content)}
    </body>
    </html>
    """
    return html


@router.get("/api/v1/legal/disclaimer", response_class=HTMLResponse)
async def disclaimer():
    """Disclaimer - HTML version"""
    md_content = LEGAL_PAGES["disclaimer"]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Disclaimer - APKDroid</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ font-size: 32px; margin-bottom: 30px; }}
            h2 {{ font-size: 24px; margin-top: 30px; margin-bottom: 15px; }}
            .warning {{ border-left: 4px solid #dc3545; padding: 15px; margin: 20px 0; background: #f8f9fa; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content)}
    </body>
    </html>
    """
    return html


@router.get("/api/v1/legal/aup", response_class=HTMLResponse)
async def acceptable_use_policy():
    """Acceptable Use Policy - HTML version"""
    md_content = LEGAL_PAGES["aup"]
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Acceptable Use Policy - APKDroid</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
            }}
            h1 {{ font-size: 32px; margin-bottom: 30px; }}
            h2 {{ font-size: 24px; margin-top: 30px; margin-bottom: 15px; }}
        </style>
    </head>
    <body>
        {markdown.markdown(md_content)}
    </body>
    </html>
    """
    return html


@router.get("/api/v1/legal", response_model=dict)
async def legal_pages_list():
    """List all available legal pages"""
    return {
        "pages": {
            "privacy": "/api/v1/legal/privacy",
            "terms": "/api/v1/legal/terms",
            "dmca": "/api/v1/legal/dmca",
            "disclaimer": "/api/v1/legal/disclaimer",
            "aup": "/api/v1/legal/aup",
        },
        "note": "All pages are also available in JSON format by appending ?format=json",
    }

