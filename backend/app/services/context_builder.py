from typing import List
import logging

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARS = 12000
MAX_SOURCES = 8


def build_context(chunks: List[dict]) -> str:
    """
    Build a grounded, deterministic context block for the LLM.
    - Sorts by similarity (best first)
    - Caps number of sources
    - Enforces character budget
    """

    if not chunks:
        logger.info("Context builder: no chunks provided")
        return ""

    # 1) Deterministic ordering
    chunks = sorted(chunks, key=lambda c: c.get("score", 1.0))

    context_parts = []
    total_len = 0
    used = 0

    for idx, c in enumerate(chunks, start=1):
        if used >= MAX_SOURCES:
            logger.info("Context builder: source cap reached (%d)", MAX_SOURCES)
            break

        try:
            block = (
                f"SOURCE {idx} (similarity={c.get('score'):.3f}):\n"
                f"[document_id={c.get('document_id')}, "
                f"pages={c.get('page_start')}-{c.get('page_end')}, "
                f"chunk_index={c.get('chunk_index')}]\n"
                f"{c.get('content')}\n"
            )
        except Exception as e:
            logger.warning("Context builder: malformed chunk skipped (%s)", e)
            continue

        if total_len + len(block) > MAX_CONTEXT_CHARS:
            logger.info(
                "Context builder: char limit reached (%d / %d)",
                total_len,
                MAX_CONTEXT_CHARS,
            )
            break

        context_parts.append(block)
        total_len += len(block)
        used += 1

    logger.info(
        "Context builder: built context | sources=%d | chars=%d",
        used,
        total_len,
    )

    return "\n".join(context_parts)
