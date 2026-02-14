from pathlib import Path, PurePath


def relative_to_home(path: Path | PurePath | str) -> str:
    """Replace the user's home directory with $HOME in a path string."""
    return str(path).replace(str(Path.home()), "$HOME")


def str2bool(v: str | None) -> bool:
    """Convert a string to a boolean value."""
    if not v:
        return False
    return str(v).lower() in ("yes", "true", "on", "1")
