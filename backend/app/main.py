from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.auth.api import router as auth_router
from app.booking.api import router as booking_router
from app.bot.webhook import router as telegram_router
from app.config import get_settings
from app.db import get_engine
from app.errors import ApiError, install_error_handlers
from app.observability.logging import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings.log_level)
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    try:
        yield
    finally:
        await app.state.arq.aclose()
        await get_engine().dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Clinic AI", version="0.1.0", lifespan=lifespan)
    install_error_handlers(app)
    origins = [*settings.cors_origins, *([settings.miniapp_url] if settings.miniapp_url else [])]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.rstrip("/") for o in origins],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    app.include_router(telegram_router)
    app.include_router(auth_router)
    app.include_router(booking_router)

    @app.get("/health", tags=["ops"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready", tags=["ops"])
    async def ready() -> dict[str, str]:
        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            await app.state.arq.ping()
        except Exception as exc:
            raise ApiError(503, "not_ready", "Dependencies unavailable") from exc
        return {"status": "ready"}

    return app


app = create_app()
