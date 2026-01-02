
def str2bool(v: str | None) -> bool:
    """Convert a string to a boolean value."""
    if not v:
        return False
    return str(v).lower() in ("yes", "true", "on", "1")
