import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base
from app.modules.files import models as file_models  # noqa: F401
from app.modules.jobs import models as job_models  # noqa: F401

# Import model modules so their tables register on Base.metadata for autogenerate.
# Backend B appends its own model modules here via a small PR.
from app.modules.users import models as _users_models  # noqa: E402,F401
from app.modules.auth import models as _auth_models  # noqa: E402,F401
from app.modules.guests import models as _guests_models  # noqa: E402,F401
from app.modules.stores import models as _stores_models  # noqa: E402,F401
from app.modules.products import models as _products_models  # noqa: E402,F401
from app.modules.cart import models as _cart_models  # noqa: E402,F401
from app.modules.orders import models as _orders_models  # noqa: E402,F401
from app.modules.owned_products import models as _owned_models  # noqa: E402,F401
from app.modules.avatars import models as _avatars_models  # noqa: E402,F401
from app.modules.try_on import models as _try_on_models  # noqa: E402,F401
from app.modules.coordis import models as _coordis_models  # noqa: E402,F401
from app.modules.diagnoses import models as _diagnoses_models  # noqa: E402,F401
from app.modules.repairs import models as _repairs_models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
