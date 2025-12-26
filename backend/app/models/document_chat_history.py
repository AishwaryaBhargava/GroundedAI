from sqlalchemy import Column, Text, Boolean, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class DocumentChatHistory(Base):
    __tablename__ = "document_chat_history"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )

    query = Column(Text, nullable=False)
    answer = Column(Text, nullable=True)

    citations = Column(JSON, nullable=False, default=list)

    refused = Column(Boolean, nullable=False, default=False)
    refusal_reason = Column(Text, nullable=True)

    model = Column(Text, nullable=True)
    token_usage = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
