from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class WorkspaceCreateRequest(BaseModel):
    name: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: UUID
    name: str
    is_guest: bool
