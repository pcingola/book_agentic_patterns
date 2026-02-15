"""Sandbox configuration loaded from config.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel

from agentic_patterns.core.config.config import MAIN_PROJECT_DIR


class SandboxProfile(BaseModel):
    """Configuration for a single sandbox profile."""

    image: str = "python:3.12-slim"
    cpu_limit: float = 1.0
    memory_limit: str = "512m"
    command_timeout: int = 30
    session_timeout: int = 3600
    container_prefix: str = "sandbox"


class SandboxConfig(BaseModel):
    """Top-level sandbox configuration with named profiles."""

    docker_host: str | None = None
    default: SandboxProfile = SandboxProfile()
    repl: SandboxProfile = SandboxProfile(image="agentic-patterns-repl:latest")


_config_cache: SandboxConfig | None = None


def load_sandbox_config(config_path: Path | None = None) -> SandboxConfig:
    """Load sandbox configuration from config.yaml or use defaults."""
    global _config_cache

    if _config_cache is not None and config_path is None:
        return _config_cache

    if config_path is None:
        config_path = MAIN_PROJECT_DIR / "config.yaml"

    if config_path.exists():
        with open(config_path) as f:
            yaml_config = yaml.safe_load(f)
            if yaml_config and "sandbox" in yaml_config:
                raw = yaml_config["sandbox"]
                # Extract top-level sandbox fields (not profiles)
                docker_host = raw.get("docker_host")
                # Profiles inherit from default: merge default values under each profile
                default_data = raw.get("default", {})
                merged: dict = {"default": default_data}
                if docker_host:
                    merged["docker_host"] = docker_host
                for name, profile_data in raw.items():
                    if name in ("default", "docker_host"):
                        continue
                    merged[name] = {**default_data, **profile_data}
                config = SandboxConfig.model_validate(merged)
                _config_cache = config
                return config

    config = SandboxConfig()
    _config_cache = config
    return config


def get_sandbox_profile(name: str = "default") -> SandboxProfile:
    """Get a sandbox profile by name. Falls back to default if not found."""
    config = load_sandbox_config()
    return getattr(config, name, config.default)
