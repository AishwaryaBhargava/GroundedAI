from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.services.embeddings import embed_texts

import logging

logger = logging.getLogger(__name__)

def _adaptive_similarity_cutoff(total_chunks: int) -> float:
    """
    Adaptive similarity threshold.
    Lower score = closer match.
    """
    if total_chunks <= 10:
        return 0.92
    if total_chunks <= 50:
        return 0.88
    return 0.85


async def retrieve_top_k_chunks(
    db: Session,
    workspace_id: str,
    query: str,
    top_k: int = 5,
    document_id: Optional[str] = None,
) -> List[dict]:
    """
    Returns top-k relevant chunks using pgvector cosine distance.
    Applies adaptive similarity cutoff to avoid false refusals
    on small, focused documents.
    """

    # 1) Embed query
    query_vec = (await embed_texts([query]))[0]

    # 2) Count total chunks in scope (for adaptive cutoff)
    count_sql = """
        SELECT COUNT(*) 
        FROM public.document_chunks
        WHERE workspace_id = :wid
          AND embedding IS NOT NULL
    """
    count_params = {"wid": workspace_id}

    if document_id:
        count_sql += " AND document_id = :did"
        count_params["did"] = document_id

    total_chunks = db.execute(
        text(count_sql), count_params
    ).scalar_one()

    similarity_cutoff = _adaptive_similarity_cutoff(total_chunks)

    logger.info(
        "Retrieval cutoff selected | workspace=%s | total_chunks=%d | cutoff=%.2f",
        workspace_id,
        total_chunks,
        similarity_cutoff,
    )

    # 3) Similarity search
    base_sql = """
        SELECT
          document_id::text AS document_id,
          chunk_index,
          page_start,
          page_end,
          token_count,
          content,
          (embedding <=> CAST(:qvec AS vector)) AS score
        FROM public.document_chunks
        WHERE workspace_id = :wid
          AND embedding IS NOT NULL
    """

    if document_id:
        base_sql += " AND document_id = :did"

    base_sql += """
        ORDER BY score ASC
        LIMIT :k
    """

    params = {
        "wid": workspace_id,
        "qvec": query_vec,
        "k": top_k,
    }

    if document_id:
        params["did"] = document_id

    rows = db.execute(text(base_sql), params).mappings().all()
    results = [dict(r) for r in rows]

    # 4) Apply adaptive cutoff
    filtered = [
        r for r in results
        if r["score"] <= similarity_cutoff
    ]

    logger.info(
        "Retrieval results | requested=%d | returned=%d",
        top_k,
        len(filtered),
    )


    return filtered
