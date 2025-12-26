from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.deps.db import get_db
from app.deps.auth import get_or_create_guest
from app.models import Guest, Workspace
from app.schemas.retrieval import RetrievalRequest
from app.schemas.answer import AnswerResponse, Citation
from app.services.retrieval import retrieve_top_k_chunks
from app.services.context_builder import build_context
from app.services.llm import generate_grounded_answer
from app.services.chat_history import append_chat_history  # ✅ NEW

router = APIRouter(prefix="/answer", tags=["Answer"])


@router.post("", response_model=AnswerResponse)
async def answer_query(
    payload: RetrievalRequest,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # ------------------------------------------------------------------
    # 1. Workspace ownership
    # ------------------------------------------------------------------
    ws = db.execute(
        select(Workspace).where(Workspace.id == payload.workspace_id)
    ).scalar_one_or_none()

    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")

    if ws.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # ------------------------------------------------------------------
    # 2. Retrieve relevant chunks
    # ------------------------------------------------------------------
    chunks = await retrieve_top_k_chunks(
        db=db,
        workspace_id=payload.workspace_id,
        query=payload.query,
        top_k=payload.top_k,
        document_id=payload.document_id,
    )

    # ------------------------------------------------------------------
    # 3. No chunks → refusal (append history if document_id exists)
    # ------------------------------------------------------------------
    if not chunks:
        if payload.document_id:
            append_chat_history(
                db=db,
                document_id=payload.document_id,
                query=payload.query,
                answer=None,
                citations=[],
                refused=True,
                refusal_reason="No relevant content found",
            )

        return AnswerResponse(
            workspace_id=payload.workspace_id,
            query=payload.query,
            answer=None,
            citations=[],
            refused=True,
            refusal_reason="No relevant content found",
        )

    # ------------------------------------------------------------------
    # 4. Build context + call LLM
    # ------------------------------------------------------------------
    context = build_context(chunks)
    llm_result = generate_grounded_answer(payload.query, context)

    # ------------------------------------------------------------------
    # 5. LLM refusal → append + return
    # ------------------------------------------------------------------
    if llm_result.get("refused"):
        if payload.document_id:
            append_chat_history(
                db=db,
                document_id=payload.document_id,
                query=payload.query,
                answer=None,
                citations=[],
                refused=True,
                refusal_reason=llm_result.get("refusal_reason"),
                model=llm_result.get("model"),
                token_usage=llm_result.get("token_usage"),
            )

        return AnswerResponse(
            workspace_id=payload.workspace_id,
            query=payload.query,
            answer=None,
            citations=[],
            refused=True,
            refusal_reason=llm_result.get("refusal_reason"),
        )

    # ------------------------------------------------------------------
    # 6. Validate citations
    # ------------------------------------------------------------------
    chunk_lookup = {
        (str(c["document_id"]), c["chunk_index"]): c
        for c in chunks
    }

    citations: list[Citation] = []
    raw_citations = llm_result.get("citations", [])

    if not isinstance(raw_citations, list):
        raise HTTPException(status_code=500, detail="Malformed citations from LLM")

    for c in raw_citations:
        if (
            not isinstance(c, dict)
            or "document_id" not in c
            or "chunk_index" not in c
        ):
            raise HTTPException(status_code=500, detail="Malformed citation structure")

        key = (str(c["document_id"]), c["chunk_index"])
        if key not in chunk_lookup:
            raise HTTPException(status_code=500, detail="Invalid citation detected")

        source_chunk = chunk_lookup[key]

        citations.append(
            Citation(
                document_id=source_chunk["document_id"],
                chunk_index=source_chunk["chunk_index"],
                page_start=source_chunk["page_start"],
                page_end=source_chunk["page_end"],
                snippet=source_chunk["content"][:300],
            )
        )

    answer_text = llm_result.get("answer")

    # ------------------------------------------------------------------
    # 7. SUCCESS → append chat history (append-only)
    # ------------------------------------------------------------------
    if payload.document_id:
        append_chat_history(
            db=db,
            document_id=payload.document_id,
            query=payload.query,
            answer=answer_text,
            citations=[c.dict() for c in citations],
            refused=False,
            refusal_reason=None,
            model=llm_result.get("model"),
            token_usage=llm_result.get("token_usage"),
        )

    # ------------------------------------------------------------------
    # 8. Return response
    # ------------------------------------------------------------------
    return AnswerResponse(
        workspace_id=payload.workspace_id,
        query=payload.query,
        answer=answer_text,
        citations=citations,
        refused=False,
        refusal_reason=None,
    )
