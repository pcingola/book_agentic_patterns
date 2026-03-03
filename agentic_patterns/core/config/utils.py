import os
from pathlib import Path
import sys


# Iterate over all parents of FILE_PATH to find .env files
def all_parents(path: Path):
    """Yield all parent directories of a given path."""
    while path.parent != path:
        yield path
        path = path.parent


def find_project_root() -> Path:
    """Find the project root by locating config.yaml.

    Resolution order:
    1. MAIN_PROJECT_DIR env var (explicit override)
    2. Walk up from cwd and main script dir looking for config.yaml
    3. Fall back to cwd
    """
    env_override = os.environ.get("MAIN_PROJECT_DIR")
    if env_override:
        return Path(env_override).resolve()

    search_roots = [Path.cwd()]
    main_mod = sys.modules.get("__main__")
    main_file = getattr(main_mod, "__file__", None)
    if main_file:
        script_dir = Path(main_file).resolve().parent
        if script_dir != search_roots[0]:
            search_roots.append(script_dir)

    for start in search_roots:
        for parent in all_parents(start):
            if (parent / "config.yaml").is_file():
                return parent

    return Path.cwd()


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
