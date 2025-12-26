from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID


class Citation(BaseModel):
    document_id: UUID
    chunk_index: int
    page_start: int
    page_end: int
    snippet: str


class AnswerResponse(BaseModel):
    workspace_id: UUID
    query: str
    answer: Optional[str]
    citations: List[Citation]
    refused: bool
    refusal_reason: Optional[str]
