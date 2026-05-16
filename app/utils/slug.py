from slugify import slugify as slug_gen


def slugify(text: str) -> str:
    """Convert text to URL-safe slug"""
    if not text:
        return ""
    return slug_gen(text, separator="-").lower()
