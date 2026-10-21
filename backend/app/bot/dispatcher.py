from functools import lru_cache

from aiogram import Bot, Dispatcher

from app.auth.crypto import decrypt
from app.bot.handlers import router
from app.tenants.models import Tenant


@lru_cache
def get_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp


_bots: dict[str, Bot] = {}


def bot_for(tenant: Tenant) -> Bot:
    """One aiogram Bot per tenant, built from its encrypted token."""
    if tenant.bot_token_enc is None:
        raise ValueError(f"tenant {tenant.slug} has no bot token")
    bot = _bots.get(tenant.slug)
    if bot is None:
        bot = Bot(token=decrypt(tenant.bot_token_enc))
        _bots[tenant.slug] = bot
    return bot


async def close_bots() -> None:
    for bot in _bots.values():
        await bot.session.close()
    _bots.clear()
