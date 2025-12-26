from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps.db import get_db
from app.deps.auth import get_or_create_guest
from app.models import Guest, Workspace
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse, RetrievalResult
from app.services.retrieval import retrieve_top_k_chunks

router = APIRouter(prefix="/query", tags=["Retrieval"])

@router.post("", response_model=RetrievalResponse)
async def query_workspace(
    payload: RetrievalRequest,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # Ownership check
    ws = db.execute(
        select(Workspace).where(Workspace.id == payload.workspace_id)
    ).scalar_one_or_none()

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if ws.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # Retrieve chunks (UNCHANGED)
    results = await retrieve_top_k_chunks(
        db=db,
        workspace_id=payload.workspace_id,
        query=payload.query,
        top_k=payload.top_k,
        document_id=payload.document_id,
    )

    # Phase 5A-2: still retrieval-only
    return RetrievalResponse(
        workspace_id=payload.workspace_id,
        query=payload.query,
        top_k=payload.top_k,
        results=[RetrievalResult(**r) for r in results],

        # NEW placeholders (no behavior change yet)
        answer=None,
        citations=None,
        refused=None,
        refusal_reason=None,
    )
