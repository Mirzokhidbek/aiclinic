import os
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from alembic import command

BACKEND = Path(__file__).resolve().parents[2]


def _docker_available() -> bool:
    try:
        import docker

        docker.from_env().ping()
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    if not _docker_available():
        pytest.skip("Docker is not available for testcontainers")
    from testcontainers.postgres import PostgresContainer

    with PostgresContainer("pgvector/pgvector:pg16", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        cfg = Config(str(BACKEND / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND / "alembic"))
        cfg.attributes["database_url"] = url
        # env.py calls asyncio.run(); keep it off the test event loop
        import threading

        t = threading.Thread(target=command.upgrade, args=(cfg, "head"))
        t.start()
        t.join()
        # Point the app's own engine/sessionmaker at the container too.
        from app.config import get_settings
        from app.db import get_engine, get_sessionmaker

        os.environ["DATABASE_URL"] = url
        get_settings.cache_clear()
        get_engine.cache_clear()
        get_sessionmaker.cache_clear()
        yield url


@pytest.fixture(scope="session")
async def sessionmaker(database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(database_url)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()
