from pathlib import Path
import sys


# Iterate over all parents of FILE_PATH to find .env files
def all_parents(path: Path):
    """Yield all parent directories of a given path."""
    while path.parent != path:
        yield path
        path = path.parent


def get_project_root() -> Path:
    """
    Return the directory where the main script lives.
    Falls back to the current working directory if run interactively.
    """
    main_mod = sys.modules.get("__main__")
    main_file = getattr(main_mod, "__file__", None)
    if main_file:
        return Path(main_file).resolve().parent

    # no __file__ (e.g. interactive shell); assume cwd is the project root
    return Path.cwd()
