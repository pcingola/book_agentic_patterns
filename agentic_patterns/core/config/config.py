from pathlib import Path

import yaml

from agentic_patterns.core.config.env import get_variable_env, load_env_variables


FILE_PATH = Path(__file__).resolve()
AGENTIC_PATTERNS_PROJECT_DIR = FILE_PATH.parent.parent.parent.resolve()

env_file = load_env_variables()

# Assign project dir based on the .env file
# Note: When this is used as a package within another project the '.env' file will be in that
# other project's directory, so MAIN_PROJECT_DIR will be that other project.
MAIN_PROJECT_DIR = Path(env_file).parent

# Directories
SCRIPTS_DIR = MAIN_PROJECT_DIR / "scripts"
DATA_DIR = Path(get_variable_env("DATA_DIR") or MAIN_PROJECT_DIR / "data")
DATA_DB_DIR = Path(get_variable_env("DATA_DB_DIR") or DATA_DIR / "db")
LOGS_DIR = MAIN_PROJECT_DIR / "logs"
PROMPTS_DIR = Path(get_variable_env("PROMPTS_DIR") or MAIN_PROJECT_DIR / "prompts")
WORKSPACE_DIR = Path(get_variable_env("WORKSPACE_DIR") or DATA_DIR / "workspaces")
PRIVATE_DATA_DIR = Path(
    get_variable_env("PRIVATE_DATA_DIR") or DATA_DIR / "private_data"
)
FEEDBACK_DIR = Path(get_variable_env("FEEDBACK_DIR") or DATA_DIR / "feedback")
SKILLS_DIR = Path(get_variable_env("SKILLS_DIR") or DATA_DIR / "skills")

# Workspace defaults
SANDBOX_PREFIX = "/workspace"
DEFAULT_USER_ID = "default_user"
DEFAULT_SESSION_ID = "default_session"


# Auth (from config.yaml, with env fallback for backward compatibility)
def _load_auth_config() -> dict:
    config_path = MAIN_PROJECT_DIR / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            cfg = yaml.safe_load(f)
            if cfg and "auth" in cfg:
                return cfg["auth"]
    return {}


_auth = _load_auth_config()
JWT_SECRET = _auth.get("jwt_secret", "dev-secret-change-in-production")
JWT_ALGORITHM = _auth.get("jwt_algorithm", "HS256")

# UI
USER_DATABASE_FILE = Path(
    get_variable_env("USER_DATABASE_FILE") or MAIN_PROJECT_DIR / "users.json"
)

# Chainlit
CHAINLIT_DATA_LAYER_DB = Path(
    get_variable_env("CHAINLIT_DATA_LAYER_DB") or DATA_DIR / "chainlit.db"
)
CHAINLIT_FILE_STORAGE_DIR = Path(
    get_variable_env("CHAINLIT_FILE_STORAGE_DIR") or DATA_DIR / "chainlit_files"
)
CHAINLIT_SCHEMA_FILE = Path(
    get_variable_env("CHAINLIT_SCHEMA_FILE")
    or DATA_DIR / "sql" / "chainlit_data_layer.sql"
)
