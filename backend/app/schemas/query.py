from pydantic import BaseModel, Field
from typing import Optional, List


class QueryRequest(BaseModel):
    workspace_id: str
    query: str
    top_k: int = 5
    document_id: Optional[str] = None  # optional filter
    include_answer: bool = False       # NEW: keep default False for safety


class RetrievedChunk(BaseModel):
    document_id: str
    chunk_index: int
    page_start: int
    page_end: int
    token_count: int
    score: float
    content: str


class Citation(BaseModel):
    document_id: str
    chunk_index: int
    page_start: int
    page_end: int
    snippet: str


class QueryResponse(BaseModel):
    workspace_id: str
    query: str
    top_k: int
    results: List[RetrievedChunk]
    answer: Optional[str] = None
    citations: Optional[List[Citation]] = None
    refused: Optional[bool] = None
    refusal_reason: Optional[str] = None
