from collections.abc import Generator
import shutil
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.main import create_app
from app.modules.avatars import models as avatar_models  # noqa: F401
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.files import models as file_models  # noqa: F401
from app.modules.guests import models as guest_models  # noqa: F401
from app.modules.jobs import models as job_models  # noqa: F401
from app.modules.products import models as product_models  # noqa: F401
from app.modules.stores import models as store_models  # noqa: F401
from app.modules.try_on import models as try_on_models  # noqa: F401
from app.modules.users import models as user_models  # noqa: F401


@pytest_asyncio.fixture(scope="session", autouse=True)
async def prepare_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    yield


@pytest.fixture(scope="session", autouse=True)
def test_file_root(tmp_path_factory: pytest.TempPathFactory) -> Generator[Path, None, None]:
    original_root = settings.file_root
    root = tmp_path_factory.mktemp("file-root")
    settings.file_root = str(root)
    yield root
    settings.file_root = original_root


@pytest_asyncio.fixture(autouse=True)
async def reset_state(test_file_root: Path) -> None:
    await engine.dispose()
    async with AsyncSessionLocal() as session:
        await session.execute(text('DELETE FROM "refreshToken"'))
        await session.execute(text('DELETE FROM "tryOn"'))
        await session.execute(text('DELETE FROM avatar'))
        await session.execute(text('DELETE FROM "productImage"'))
        await session.execute(text('DELETE FROM "productTag"'))
        await session.execute(text('DELETE FROM "productVariant"'))
        await session.execute(text('DELETE FROM product'))
        await session.execute(text('DELETE FROM "guestSession"'))
        await session.execute(text('DELETE FROM "qrCodeMapping"'))
        await session.execute(text('DELETE FROM campaign'))
        await session.execute(text('DELETE FROM store'))
        await session.execute(text('DELETE FROM "user"'))
        await session.execute(text('DELETE FROM "job"'))
        await session.execute(text('DELETE FROM "fileMetadata"'))
        await session.commit()

    shutil.rmtree(test_file_root, ignore_errors=True)
    test_file_root.mkdir(parents=True, exist_ok=True)
    yield

    await engine.dispose()
    async with AsyncSessionLocal() as session:
        await session.execute(text('DELETE FROM "refreshToken"'))
        await session.execute(text('DELETE FROM "tryOn"'))
        await session.execute(text('DELETE FROM avatar'))
        await session.execute(text('DELETE FROM "productImage"'))
        await session.execute(text('DELETE FROM "productTag"'))
        await session.execute(text('DELETE FROM "productVariant"'))
        await session.execute(text('DELETE FROM product'))
        await session.execute(text('DELETE FROM "guestSession"'))
        await session.execute(text('DELETE FROM "qrCodeMapping"'))
        await session.execute(text('DELETE FROM campaign'))
        await session.execute(text('DELETE FROM store'))
        await session.execute(text('DELETE FROM "user"'))
        await session.execute(text('DELETE FROM "job"'))
        await session.execute(text('DELETE FROM "fileMetadata"'))
        await session.commit()

    shutil.rmtree(test_file_root, ignore_errors=True)
    test_file_root.mkdir(parents=True, exist_ok=True)


@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    with TestClient(create_app()) as test_client:
        yield test_client
