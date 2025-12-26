from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

import os

from app.deps.db import get_db
from app.deps.auth import get_or_create_guest
from app.models import Guest, Workspace, Document, DocumentChunk
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/documents", tags=["Embeddings"])


@router.post("/{document_id}/embed")
async def embed_document(
    document_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # Fetch document
    doc = db.execute(select(Document).where(Document.id == document_id)).scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Ownership check via workspace -> guest
    ws = db.execute(select(Workspace).where(Workspace.id == doc.workspace_id)).scalar_one_or_none()
    if not ws or ws.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    batch_size = int(os.getenv("EMBED_BATCH_SIZE", "8"))

    # Load chunks needing embeddings
    chunks = db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc.id)
        .where(DocumentChunk.embedding.is_(None))
        .order_by(DocumentChunk.chunk_index.asc())
    ).scalars().all()

    if not chunks:
        # already embedded (or no chunks)
        return {"document_id": str(doc.id), "embedded_chunks": 0, "status": getattr(doc, "status", "unknown")}

    # Mark doc as embedding (if you use status)
    if hasattr(doc, "status"):
        doc.status = "embedding"
        db.commit()

    embedded = 0

    # Batch loop
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [c.content for c in batch]

        try:
            vectors = await embed_texts(texts)
        except Exception as e:
            # mark failed and exit cleanly
            if hasattr(doc, "status"):
                doc.status = "failed_embedding"
                db.commit()
            raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")

        # Write embeddings back (same order)
        for c, v in zip(batch, vectors):
            c.embedding = v
            embedded += 1

        db.commit()

    # Mark doc embedded
    if hasattr(doc, "status"):
        doc.status = "embedded"
        db.commit()

    return {"document_id": str(doc.id), "embedded_chunks": embedded, "status": getattr(doc, "status", "embedded")}
