from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    created_at: datetime


class DocumentListResponse(BaseModel):
    id: UUID
    filename: str
    status: str
    file_type: str
    file_size: int
    created_at: datetime
