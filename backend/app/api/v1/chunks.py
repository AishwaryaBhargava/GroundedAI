from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps.db import get_db
from app.deps.auth import get_or_create_guest
from app.models import DocumentChunk, Guest, Workspace, Document

router = APIRouter(prefix="/documents", tags=["chunks"])


@router.get("/{document_id}/chunks")
def list_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Check workspace ownership (guest)
    ws = db.execute(select(Workspace).where(Workspace.id == doc.workspace_id)).scalar_one_or_none()
    if not ws or ws.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    rows = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .order_by(DocumentChunk.chunk_index.asc())
    ).scalars().all()

    return [
        {
            "chunk_index": r.chunk_index,
            "page_start": r.page_start,
            "page_end": r.page_end,
            "token_count": r.token_count,
            "content_preview": (r.content[:300] + "...") if len(r.content) > 300 else r.content,
        }
        for r in rows
    ]
