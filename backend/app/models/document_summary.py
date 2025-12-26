from sqlalchemy import Column, ForeignKey, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import TIMESTAMP

from app.core.database import Base


class DocumentSummary(Base):
    __tablename__ = "document_summaries"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )

    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )

    bullet_points = Column(JSONB, nullable=False, default=list)
    narrative_summary = Column(Text, nullable=False, default="")
    suggested_questions = Column(JSONB, nullable=False, default=list)

    status = Column(Text, nullable=False, default="pending")
    error_reason = Column(Text, nullable=True)

    model = Column(Text, nullable=True)
    token_usage = Column(Integer, nullable=True)

    created_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at = Column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
