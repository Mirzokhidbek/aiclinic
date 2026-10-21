from aiogram import F, Router
from aiogram.enums import ChatAction
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.conversation.pipeline import Deps, IncomingMessage, Reply, handle_customer_message
from app.tenants.models import Tenant

router = Router(name="customer")

WELCOME = (
    "Assalomu alaykum! Men {name} yordamchisiman. "
    "Xizmatlar, narxlar yoki ish vaqti haqida savol bering."
)


def render(reply: Reply) -> str:
    if not reply.sources:
        return reply.text
    # The model is asked to cite inline; add the retrieved titles only if it didn't.
    if any(title in reply.text for title in reply.sources):
        return reply.text
    return f"{reply.text}\n\n📄 Manba: {', '.join(reply.sources)}"


def miniapp_url(base: str, tenant: Tenant) -> str | None:
    """Telegram only opens Mini Apps over HTTPS; return None until one is configured."""
    if not base.startswith("https://"):
        return None
    return f"{base.rstrip('/')}/?tenant={tenant.slug}"


@router.message(CommandStart())
async def on_start(message: Message, tenant: Tenant, deps: Deps) -> None:
    url = miniapp_url(deps.settings.miniapp_url, tenant)
    markup = (
        InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Qabulga yozilish", web_app=WebAppInfo(url=url))]
            ]
        )
        if url
        else None
    )
    await message.answer(WELCOME.format(name=tenant.name), reply_markup=markup)


@router.message(F.text)
async def on_text(message: Message, tenant: Tenant, deps: Deps) -> None:
    if message.from_user is None or message.text is None:
        return
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)  # type: ignore[union-attr]
    reply = await handle_customer_message(
        deps,
        tenant,
        IncomingMessage(
            telegram_id=message.from_user.id,
            name=message.from_user.full_name,
            language=message.from_user.language_code,
            text=message.text,
        ),
    )
    await message.answer(render(reply))


@router.message()
async def on_other(message: Message) -> None:
    await message.answer("Hozircha faqat matnli xabarlarni tushunaman.")
