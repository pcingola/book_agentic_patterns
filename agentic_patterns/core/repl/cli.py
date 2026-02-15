"""CLI to build the REPL Docker image."""

import subprocess
import sys
from pathlib import Path

from agentic_patterns.core.sandbox.config import load_sandbox_config

DOCKER_DIR = Path(__file__).parent / "docker"
IMAGE_TAG = "agentic-patterns-repl:latest"


def main() -> None:
    docker_host = load_sandbox_config().docker_host
    cmd = ["docker", "build", "-t", IMAGE_TAG, "--rm", str(DOCKER_DIR)]
    if docker_host:
        cmd = ["docker", "-H", docker_host] + cmd[1:]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
