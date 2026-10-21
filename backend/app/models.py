"""Import every model so Alembic and metadata see the full schema."""

from app.booking.models import Booking, Service, Slot
from app.conversation.models import Conversation, Customer, Message
from app.retrieval.models import Chunk, Document
from app.tenants.models import Tenant

__all__ = [
    "Booking",
    "Chunk",
    "Conversation",
    "Customer",
    "Document",
    "Message",
    "Service",
    "Slot",
    "Tenant",
]
