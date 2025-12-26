from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.core.database import Base


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    owner_guest_id = Column(UUID(as_uuid=True), ForeignKey("guests.id"), nullable=True)

    name = Column(String, nullable=False)
    is_guest = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="workspaces")
    guest = relationship("Guest", back_populates="workspaces")
