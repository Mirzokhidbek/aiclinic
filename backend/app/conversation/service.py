import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.conversation.models import Conversation, Customer, Message


async def upsert_customer(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    telegram_id: int,
    name: str | None,
    language: str | None,
) -> Customer:
    stmt = (
        insert(Customer)
        .values(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            telegram_id=telegram_id,
            name=name,
            language=language,
        )
        .on_conflict_do_update(
            index_elements=[Customer.tenant_id, Customer.telegram_id],
            set_={"name": name, "language": language},
        )
        .returning(Customer)
    )
    result = await session.execute(stmt)
    return result.scalar_one()


async def get_open_conversation(
    session: AsyncSession, tenant_id: uuid.UUID, customer_id: uuid.UUID
) -> Conversation:
    result = await session.execute(
        select(Conversation)
        .where(
            Conversation.tenant_id == tenant_id,
            Conversation.customer_id == customer_id,
            Conversation.status != "closed",
        )
        .order_by(Conversation.updated_at.desc())
        .limit(1)
    )
    conversation = result.scalar_one_or_none()
    if conversation is None:
        conversation = Conversation(tenant_id=tenant_id, customer_id=customer_id, status="ai")
        session.add(conversation)
        await session.flush()
    return conversation


async def recent_turns(
    session: AsyncSession, conversation_id: uuid.UUID, limit: int = 8
) -> list[Message]:
    """Last `limit` customer/assistant messages, oldest first."""
    result = await session.execute(
        select(Message)
        .where(
            Message.conversation_id == conversation_id,
            Message.role.in_(("customer", "assistant")),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))


async def add_message(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    **fields: Any,
) -> Message:
    message = Message(
        tenant_id=tenant_id, conversation_id=conversation_id, role=role, content=content, **fields
    )
    session.add(message)
    await session.flush()
    return message
