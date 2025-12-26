from typing import Dict, List
from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models import DocumentChunk, DocumentSummary
from app.services.llm import get_summary_completion

# -----------------------------
# Limits & constraints
# -----------------------------
MAX_SUMMARY_CHARS = 16000

MIN_BULLETS = 5
MAX_BULLETS = 10

MIN_QUESTIONS = 5
MAX_QUESTIONS = 8

MAX_NARRATIVE_CHARS = 4000


# -----------------------------
# Helpers
# -----------------------------
def _build_document_context(chunks: List[DocumentChunk]) -> str:
    """
    Concatenate document chunks into a bounded context window.
    """
    parts: List[str] = []
    total_len = 0

    for c in chunks:
        block = (
            f"[pages {c.page_start}-{c.page_end}, chunk {c.chunk_index}]\n"
            f"{c.content}\n"
        )

        if total_len + len(block) > MAX_SUMMARY_CHARS:
            break

        parts.append(block)
        total_len += len(block)

    return "\n".join(parts)


def _validate_summary_output(parsed: Dict) -> Dict:
    """
    Hard validation of LLM summary output.
    Raises ValueError on ANY violation.
    """

    for key in ("bullet_points", "narrative_summary", "suggested_questions"):
        if key not in parsed:
            raise ValueError(f"Missing field: {key}")

    bullets = parsed["bullet_points"]
    narrative = parsed["narrative_summary"]
    questions = parsed["suggested_questions"]

    if not isinstance(bullets, list) or not all(isinstance(b, str) for b in bullets):
        raise ValueError("bullet_points must be list[str]")

    if not isinstance(questions, list) or not all(isinstance(q, str) for q in questions):
        raise ValueError("suggested_questions must be list[str]")

    if not isinstance(narrative, str) or not narrative.strip():
        raise ValueError("narrative_summary must be non-empty string")

    if not (MIN_BULLETS <= len(bullets) <= MAX_BULLETS):
        raise ValueError("Invalid number of bullet_points")

    if not (MIN_QUESTIONS <= len(questions) <= MAX_QUESTIONS):
        raise ValueError("Invalid number of suggested_questions")

    if len(narrative) > MAX_NARRATIVE_CHARS:
        raise ValueError("narrative_summary too long")

    return {
        "bullet_points": [b.strip() for b in bullets],
        "narrative_summary": narrative.strip(),
        "suggested_questions": [q.strip() for q in questions],
    }


# -----------------------------
# Main service
# -----------------------------
def generate_document_summary(
    db: Session,
    document_id: str,
) -> Dict:
    """
    Always generates a fresh summary for the document.
    Overwrites existing summary deterministically.
    """

    # ---- fetch document chunks ----
    chunks = (
        db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )
        .scalars()
        .all()
    )

    if not chunks:
        raise ValueError("No chunks found for document")

    context = _build_document_context(chunks)

    # ---- get or create summary row ----
    summary = (
        db.execute(
            select(DocumentSummary)
            .where(DocumentSummary.document_id == document_id)
        )
        .scalar_one_or_none()
    )

    if not summary:
        summary = DocumentSummary(
            document_id=document_id,
            status="running",
            created_at=datetime.utcnow(),
        )
        db.add(summary)
    else:
        summary.status = "running"
        summary.error_reason = None

    summary.updated_at = datetime.utcnow()
    db.commit()

    # ---- LLM call + validation ----
    try:
        raw = get_summary_completion(context)

        validated = _validate_summary_output(raw["summary"])
        meta = raw.get("meta", {})

        summary.bullet_points = validated["bullet_points"]
        summary.narrative_summary = validated["narrative_summary"]
        summary.suggested_questions = validated["suggested_questions"]

        summary.model = meta.get("model")
        summary.token_usage = meta.get("token_usage")

        summary.status = "completed"
        summary.updated_at = datetime.utcnow()

        db.commit()
        return validated

    except Exception as e:
        summary.status = "failed"
        summary.error_reason = str(e)
        summary.updated_at = datetime.utcnow()
        db.commit()
        raise
