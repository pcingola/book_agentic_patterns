"""CLI to build the REPL Docker image."""

import sys
from pathlib import Path

import docker


DOCKER_DIR = Path(__file__).parent / "docker"
DEFAULT_IMAGE = "agentic-patterns-repl:latest"


def main() -> None:
    image_tag = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IMAGE
    client = docker.from_env()
    client.images.build(path=str(DOCKER_DIR), tag=image_tag, rm=True)


if __name__ == "__main__":
    main()
