# app/services/chat_history.py

from typing import List, Dict, Optional
from sqlalchemy.orm import Session

from app.models import DocumentChatHistory


def _serialize_citations(citations: List[Dict]) -> List[Dict]:
    """
    Ensure citations are JSON-serializable.
    """
    serialized = []

    for c in citations:
        serialized.append(
            {
                "document_id": str(c["document_id"]),
                "chunk_index": c["chunk_index"],
                "page_start": c.get("page_start"),
                "page_end": c.get("page_end"),
                "snippet": c.get("snippet"),
            }
        )

    return serialized


def append_chat_history(
    db: Session,
    document_id: str,
    query: str,
    answer: Optional[str],
    citations: List[Dict],
    refused: bool,
    refusal_reason: Optional[str],
    model: Optional[str] = None,
    token_usage: Optional[int] = None,
):
    row = DocumentChatHistory(
        document_id=document_id,
        query=query,
        answer=answer,
        citations=_serialize_citations(citations),
        refused=refused,
        refusal_reason=refusal_reason,
        model=model,
        token_usage=token_usage,
    )

    db.add(row)
    db.commit()
