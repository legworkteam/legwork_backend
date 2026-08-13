from __future__ import annotations

from pathlib import Path

import anyio

from app.core.config import settings
from app.storage.base import StorageService, StorageWriteResult


class LocalStorageService(StorageService):
    def __init__(self, file_root: str | Path | None = None) -> None:
        self.file_root = Path(file_root or settings.file_root).resolve()

    def _resolve(self, relative_path: str) -> Path:
        candidate = (self.file_root / relative_path).resolve()
        candidate.relative_to(self.file_root)
        return candidate

    async def save(self, *, relative_path: str, content: bytes) -> StorageWriteResult:
        destination = self._resolve(relative_path)
        await anyio.to_thread.run_sync(lambda: destination.parent.mkdir(parents=True, exist_ok=True))
        await anyio.to_thread.run_sync(destination.write_bytes, content)
        return StorageWriteResult(relative_path=relative_path, absolute_path=destination, size=len(content))

    async def open(self, *, relative_path: str) -> bytes:
        source = self._resolve(relative_path)
        return await anyio.to_thread.run_sync(source.read_bytes)

    async def delete(self, *, relative_path: str) -> None:
        target = self._resolve(relative_path)

        def _delete() -> None:
            if target.exists():
                target.unlink()

        await anyio.to_thread.run_sync(_delete)
