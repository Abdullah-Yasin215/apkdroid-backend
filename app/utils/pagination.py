def paginate(skip: int = 0, limit: int = 24):
    """Validate and return pagination parameters"""
    skip = max(0, skip)
    limit = min(100, max(1, limit))
    return skip, limit
