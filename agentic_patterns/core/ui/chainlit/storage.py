"""Filesystem-based storage provider for Chainlit."""

from logging import getLogger
from pathlib import Path
from typing import Any

from chainlit.data.storage_clients.base import BaseStorageClient

from agentic_patterns.core.config.config import CHAINLIT_FILE_STORAGE_DIR

logger = getLogger(__name__)


class FilesystemStorageClient(BaseStorageClient):
    """Storage provider that uses the local filesystem."""

    def __init__(self, storage_dir: Path = CHAINLIT_FILE_STORAGE_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"FilesystemStorageClient initialized at {self.storage_dir}")

    async def close(self) -> None:
        pass

    async def delete_file(self, object_key: str) -> bool:
        try:
            file_path = self.storage_dir / object_key
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception as e:
            logger.warning(f"FilesystemStorageClient, delete_file error: {e}")
            return False

    async def get_read_url(self, object_key: str) -> str:
        file_path = self.storage_dir / object_key
        return str(file_path.absolute())

    async def upload_file(
        self,
        object_key: str,
        data: bytes | str,
        mime: str = "application/octet-stream",
        overwrite: bool = True,
        content_disposition: str | None = None,
    ) -> dict[str, Any]:
        try:
            file_path = self.storage_dir / object_key
            file_path.parent.mkdir(parents=True, exist_ok=True)
            if not overwrite and file_path.exists():
                logger.warning(f"File already exists and overwrite=False: {file_path}")
                return {}
            mode = "wb" if isinstance(data, bytes) else "w"
            with open(file_path, mode) as f:
                f.write(data)
            url = str(file_path.absolute())
            return {"object_key": object_key, "url": url}
        except Exception as e:
            logger.warning(f"FilesystemStorageClient, upload_file error: {e}")
            return {}
