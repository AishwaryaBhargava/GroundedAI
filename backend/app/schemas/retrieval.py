from pydantic import BaseModel, Field
from typing import List, Optional


class RetrievalRequest(BaseModel):
    workspace_id: str
    query: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=20)
    document_id: Optional[str] = None  # optional filter later
    include_answer: bool = False


class RetrievalResult(BaseModel):
    document_id: str
    chunk_index: int
    page_start: int
    page_end: int
    token_count: int
    score: float  # cosine distance (lower = better)
    content: str


class RetrievalResponse(BaseModel):
    workspace_id: str
    query: str
    top_k: int
    results: List[RetrievalResult]
    # Phase 5A additions (unused for now)
    answer: Optional[str] = None
    citations: Optional[list] = None
    refused: Optional[bool] = None
    refusal_reason: Optional[str] = None
