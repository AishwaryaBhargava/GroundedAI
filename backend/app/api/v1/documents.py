from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4
from sqlalchemy import select

from app.deps.db import get_db
from app.deps.auth import get_or_create_guest
from app.models import Document, Workspace, Guest, DocumentChunk, DocumentSummary, DocumentChatHistory
from app.services.storage import upload_document, get_document_signed_url
from app.schemas.document import DocumentUploadResponse, DocumentListResponse
from app.services.pdf_extract import extract_pages
from app.services.chunking import chunk_pages_token_based
from app.services.summary import generate_document_summary

router = APIRouter(prefix="/documents", tags=["Documents"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_TYPES = {
    "application/pdf",
    "text/plain",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/csv",
}


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document_api(
    workspace_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # Validate workspace ownership
    workspace = db.query(Workspace).filter_by(
        id=workspace_id,
        owner_guest_id=guest.id
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Guest doc limit
    if guest and workspace.is_guest:
        count = db.query(Document).filter_by(workspace_id=workspace.id).count()
        if count >= 10:
            raise HTTPException(status_code=403, detail="Guest documents limit reached")

    # File type
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    contents = await file.read()

    # File size
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large")

    # Upload to Supabase Storage
    storage_path = upload_document(
        file_bytes=contents,
        filename=file.filename,
        content_type=file.content_type,
    )

    # Save DB record
    doc = Document(
        id=uuid4(),
        workspace_id=workspace.id,
        filename=file.filename,
        file_type=file.content_type,
        file_size=len(contents),
        storage_path=storage_path,
        status="uploaded",
    )

    db.add(doc)
    db.commit()
    db.refresh(doc)

    # ---- Phase 1D: extract + chunk + store ----
    # pages = extract_pages(contents)

    from app.services.extraction import extract_document

    extracted = extract_document(
        file_bytes=contents,
        content_type=file.content_type,
        filename=file.filename,
    )
    pages = extracted.pages


    chunks = chunk_pages_token_based(
        pages,
        chunk_tokens=500,
        overlap_tokens=100,
    )

    # Bulk insert chunks
    chunk_rows = [
        DocumentChunk(
            document_id=doc.id,
            workspace_id=workspace.id,
            chunk_index=c.chunk_index,
            page_start=c.page_start,
            page_end=c.page_end,
            token_count=c.token_count,
            content=c.content,
        )
        for c in chunks
    ]

    db.add_all(chunk_rows)
    db.commit()


    return DocumentUploadResponse(
        id=doc.id,
        filename=doc.filename,
        status=doc.status,
        created_at=doc.created_at,
    )


@router.get("", response_model=list[DocumentListResponse])
def list_documents(
    workspace_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    workspace = db.query(Workspace).filter_by(
        id=workspace_id,
        owner_guest_id=guest.id,
    ).first()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    rows = db.execute(
        select(Document)
        .where(Document.workspace_id == workspace.id)
        .order_by(Document.created_at.desc())
    ).scalars().all()

    return [
        DocumentListResponse(
            id=d.id,
            filename=d.filename,
            status=d.status,
            file_type=d.file_type,
            file_size=d.file_size,
            created_at=d.created_at,
        )
        for d in rows
    ]


@router.get("/{document_id}/file-url")
def get_document_file_url(
    document_id: str,
    expires_in: int = 3600,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    document = db.execute(
        select(Document).where(Document.id == document_id)
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    workspace = db.execute(
        select(Workspace).where(Workspace.id == document.workspace_id)
    ).scalar_one_or_none()

    if not workspace or workspace.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    try:
        url = get_document_signed_url(document.storage_path, expires_in=expires_in)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "document_id": document_id,
        "url": url,
        "expires_in": expires_in,
    }

@router.get("/{document_id}/summary")
def get_document_summary(
    document_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # ---- Fetch document ----
    document = db.execute(
        select(Document).where(Document.id == document_id)
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # ---- Ownership check ----
    workspace = db.execute(
        select(Workspace).where(Workspace.id == document.workspace_id)
    ).scalar_one_or_none()

    if not workspace or workspace.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # ---- Fetch summary ----
    summary = db.execute(
        select(DocumentSummary)
        .where(DocumentSummary.document_id == document_id)
    ).scalar_one_or_none()

    if not summary:
        return {
            "document_id": document_id,
            "status": "not_started",
        }

    if summary.status == "running":
        return {
            "document_id": document_id,
            "status": "running",
        }

    if summary.status == "failed":
        return {
            "document_id": document_id,
            "status": "failed",
            "error_reason": summary.error_reason,
        }

    # ---- Completed ----
    return {
        "document_id": document_id,
        "status": "completed",
        "bullet_points": summary.bullet_points,
        "narrative_summary": summary.narrative_summary,
        "suggested_questions": summary.suggested_questions,
        "model": summary.model,
        "token_usage": summary.token_usage,
        "updated_at": summary.updated_at,
    }

@router.post("/{document_id}/summary")
def generate_summary(
    document_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # ---- Fetch document ----
    document = db.execute(
        select(Document).where(Document.id == document_id)
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # ---- Ownership check ----
    workspace = db.execute(
        select(Workspace).where(Workspace.id == document.workspace_id)
    ).scalar_one_or_none()

    if not workspace or workspace.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # ---- Generate summary (always) ----
    try:
        summary = generate_document_summary(db, document_id)
        return {
            "document_id": document_id,
            "status": "completed",
            **summary,
        }

    except ValueError as e:
        # Logical / data issues
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        # Unexpected failures already recorded in DB
        raise HTTPException(
            status_code=500,
            detail="Summary generation failed",
        )

@router.get("/{document_id}/chat")
def get_document_chat_history(
    document_id: str,
    db: Session = Depends(get_db),
    guest: Guest = Depends(get_or_create_guest),
):
    # 1. Fetch document
    document = (
        db.execute(
            select(Document).where(Document.id == document_id)
        )
        .scalar_one_or_none()
    )

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # 2. Workspace ownership check
    workspace = (
        db.execute(
            select(Workspace).where(Workspace.id == document.workspace_id)
        )
        .scalar_one_or_none()
    )

    if not workspace or workspace.owner_guest_id != guest.id:
        raise HTTPException(status_code=403, detail="Not allowed")

    # 3. Fetch chat history (append-only)
    rows = (
        db.execute(
            select(DocumentChatHistory)
            .where(DocumentChatHistory.document_id == document_id)
            .order_by(DocumentChatHistory.created_at.asc())
        )
        .scalars()
        .all()
    )

    # 4. Serialize
    messages = [
        {
            "id": r.id,
            "query": r.query,
            "answer": r.answer,
            "citations": r.citations,
            "refused": r.refused,
            "refusal_reason": r.refusal_reason,
            "model": r.model,
            "token_usage": r.token_usage,
            "created_at": r.created_at,
        }
        for r in rows
    ]

    return {
        "document_id": document_id,
        "messages": messages,
    }
