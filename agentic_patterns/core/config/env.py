
import logging
import os
from pathlib import Path
import sys
from dotenv import dotenv_values, find_dotenv, load_dotenv

from agentic_patterns.core.config.utils import all_parents, get_project_root


logger = logging.getLogger(__name__)


def find_env_file(env_search_dirs: list[Path]) -> str | None:
    """Find the first .env file in the given list of paths and their parents."""
    env_file = find_dotenv()
    logging.warning("Looking for '.env' file in default directory")
    if env_file:
        return env_file
    # Find all parents of the paths
    for search_dir in env_search_dirs:
        # '.env' file in this directory?
        logging.warning("Looking for '.env' file at '%s'", search_dir)
        env_file = find_dotenv(str(search_dir / ".env"))
        if env_file:
            return env_file
        # Try all parents of this dir
        for parent_dir in all_parents(search_dir):
            logging.warning("Looking for '.env' file at '%s'", parent_dir)
            env_file = find_dotenv(str(parent_dir / ".env"))
            if env_file:
                return env_file
    return None


def get_variable_env(name: str, allow_empty=True, default=None) -> str | None:
    """Retrieve environment variable with optional validation and default value."""
    val = os.environ.get(name, default)
    if not allow_empty and ((val is None) or (val == "")):
        raise ValueError(f"Environment variable {name} is not set")
    return val


def load_env_variables():
    # Set up environment search path
    # Start with the most specific (current directory) and expand outward
    # This file's path
    file_path = Path(__file__).resolve()
    env_dirs = [Path.cwd(), get_project_root(), file_path.parent]
    env_file = find_env_file(env_dirs)

    if env_file:
        logger.info("Using .env file at '%s'", env_file)
        # Load the environment variables from the found .env file
        load_dotenv(env_file)
        # Assign variables in '.env' global python environment
        env_vars = dotenv_values(env_file)
        globals().update(env_vars)

        return env_file
    else:
        logger.error("No '.env' file found in any of the search paths, or their parents: %s", env_dirs)
        sys.exit(1)
