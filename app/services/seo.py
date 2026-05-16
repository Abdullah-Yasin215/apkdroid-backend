def generate_app_schema(app_data: dict) -> dict:
    """Generate JSON-LD schema markup for an app"""
    schema = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": app_data.get("name", ""),
        "operatingSystem": "Android",
        "applicationCategory": app_data.get("category", ""),
        "offers": {
            "@type": "Offer",
            "price": "0" if app_data.get("is_free") else str(app_data.get("price", 0)),
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock"
        },
        "aggregateRating": {
            "@type": "AggregateRating",
            "ratingValue": float(app_data.get("rating", 0)),
            "ratingCount": app_data.get("rating_count", 0),
            "bestRating": "5",
            "worstRating": "1"
        },
        "image": app_data.get("icon_url", ""),
        "description": app_data.get("short_desc", ""),
        "softwareVersion": app_data.get("latest_version", ""),
        "fileSize": app_data.get("size", ""),
        "downloadUrl": f"https://apkdroid.net/app/{app_data.get('slug', '')}/download"
    }
    return schema
