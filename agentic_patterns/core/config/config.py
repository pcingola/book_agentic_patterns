
from pathlib import Path

from agentic_patterns.core.config.env import get_variable_env, load_env_variables
from agentic_patterns.core.config.utils import get_project_root
from agentic_patterns.core.utils import str2bool


FILE_PATH = Path(__file__).resolve()
AGENTIC_PATTERNS_PROJECT_DIR = FILE_PATH.parent.parent.parent.resolve()

# Get the main project directory (the one project that is using this package)
PROJECT_ROOT = get_project_root()

env_file = load_env_variables()

# Assign project dir based on the .env file
# Note: When this is used as a package witihn another project the '.env' file will be in that
# other project's directory, so MAIN_PROJECT_DIR will be that other project.
MAIN_PROJECT_DIR = Path(env_file).parent


# Get the main project directory (the one project that is using this package)
PROJECT_ROOT = get_project_root()
SCRIPTS_DIR = MAIN_PROJECT_DIR / "scripts"
DATA_DIR = Path(get_variable_env("DATA_DIR") or MAIN_PROJECT_DIR / "data")
DATA_DB_DIR = Path(get_variable_env("DATA_DB_DIR") or DATA_DIR / "db")
LOGS_DIR = MAIN_PROJECT_DIR / "logs"
PROMPTS_DIR = Path(get_variable_env("PROMPTS_DIR") or MAIN_PROJECT_DIR / "prompts")


# ---
# Directories
# ---
SCRIPTS_DIR = MAIN_PROJECT_DIR / "scripts"
DATA_DIR = Path(get_variable_env("DATA_DIR") or MAIN_PROJECT_DIR / "data")
DATA_DB_DIR = Path(get_variable_env("DATA_DB_DIR") or DATA_DIR / "db")
LOGS_DIR = MAIN_PROJECT_DIR / "logs"
PROMPTS_DIR = Path(get_variable_env("PROMPTS_DIR") or MAIN_PROJECT_DIR / "prompts")

#---
# Variables in '.env' file
# Explicitly load specific variables
#---

# Models
MODEL_FAMILY = get_variable_env("MODEL_FAMILY")
MODEL_TIMEOUT = int(get_variable_env("MODEL_TIMEOUT", default="120"))  # type: ignore

# Azure models
AZURE_MODEL_NAME = get_variable_env("AZURE_MODEL_NAME")
AZURE_OPENAI_ENDPOINT = get_variable_env("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = get_variable_env("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = get_variable_env("AZURE_OPENAI_API_VERSION")

# OpenAI models
OPENAI_API_KEY = get_variable_env("OPENAI_API_KEY")
OPENAI_MODEL_NAME = get_variable_env("OPENAI_MODEL_NAME")

# Ollama models
OLLAMA_URL = get_variable_env("OLLAMA_URL")
OLLAMA_MODEL_NAME = get_variable_env("OLLAMA_MODEL_NAME")

# OpenRouter models
OPENROUTER_API_KEY = get_variable_env("OPENROUTER_API_KEY")
OPENROUTER_API_URL = get_variable_env("OPENROUTER_API_URL", default="https://openrouter.ai/api/v1")
OPENROUTER_MODEL_NAME = get_variable_env("OPENROUTER_MODEL_NAME")

# Embeddings
VDB_EMBEDDINGS_MODEL_FAMILY = get_variable_env("VDB_EMBEDDINGS_MODEL_FAMILY")
OPENAI_VDB_EMBEDDINGS_MODEL_NAME = get_variable_env("OPENAI_VDB_EMBEDDINGS_MODEL_NAME")
AZURE_VDB_EMBEDDINGS_MODEL_NAME = get_variable_env("AZURE_VDB_EMBEDDINGS_MODEL_NAME")
OLLAMA_VDB_EMBEDDINGS_MODEL_NAME = get_variable_env("OLLAMA_VDB_EMBEDDINGS_MODEL_NAME")

# Bedrock models
AWS_ACCESS_KEY_ID = get_variable_env("AWS_ACCESS_KEY_ID", allow_empty=True)
AWS_SECRET_ACCESS_KEY = get_variable_env("AWS_SECRET_ACCESS_KEY", allow_empty=True)
AWS_SESSION_TOKEN = get_variable_env("AWS_SESSION_TOKEN", allow_empty=True)
AWS_REGION = get_variable_env("AWS_REGION", allow_empty=True, default="us-east-1")
AWS_PROFILE = get_variable_env("AWS_PROFILE", allow_empty=True)
BEDROCK_MODEL_NAME = get_variable_env("BEDROCK_MODEL_NAME", allow_empty=True)
BEDROCK_CLAUDE_SONNET_1M_TOKENS = str2bool(get_variable_env("BEDROCK_CLAUDE_SONNET_1M_TOKENS", allow_empty=True, default="False"))

# Google Vertex AI
GOOGLE_CLOUD_PROJECT = get_variable_env("GOOGLE_CLOUD_PROJECT", True)
GOOGLE_CLOUD_LOCATION = get_variable_env("GOOGLE_CLOUD_LOCATION", True)
