from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class StorageWriteResult:
    relative_path: str
    absolute_path: Path
    size: int


class StorageService(Protocol):
    async def save(self, *, relative_path: str, content: bytes) -> StorageWriteResult: ...

    async def open(self, *, relative_path: str) -> bytes: ...

    async def delete(self, *, relative_path: str) -> None: ...
