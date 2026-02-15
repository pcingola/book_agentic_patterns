"""CLI to build the REPL Docker image."""

import subprocess
import sys
from pathlib import Path

from agentic_patterns.core.sandbox.config import DOCKER_HOST

DOCKER_DIR = Path(__file__).parent / "docker"
IMAGE_TAG = "agentic-patterns-repl:latest"


def main() -> None:
    cmd = ["docker", "build", "-t", IMAGE_TAG, "--rm", str(DOCKER_DIR)]
    if DOCKER_HOST:
        cmd = ["docker", "-H", DOCKER_HOST] + cmd[1:]
    sys.exit(subprocess.call(cmd))


if __name__ == "__main__":
    main()
