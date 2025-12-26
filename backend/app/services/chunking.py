from dataclasses import dataclass
import tiktoken


@dataclass
class Chunk:
    chunk_index: int
    page_start: int
    page_end: int
    token_count: int
    content: str


def chunk_pages_token_based(
    pages: list[dict],
    chunk_tokens: int = 500,
    overlap_tokens: int = 100,
    encoding_name: str = "cl100k_base",
) -> list[Chunk]:
    """
    pages: [{page: int, text: str}]
    Returns list of chunks with page ranges + token counts.
    """
    if overlap_tokens >= chunk_tokens:
        raise ValueError("overlap_tokens must be < chunk_tokens")

    enc = tiktoken.get_encoding(encoding_name)

    # Build a flat stream of (page, text) while preserving page boundaries
    units = []
    for p in pages:
        txt = (p.get("text") or "").strip()
        if txt:
            units.append((p["page"], txt))

    chunks: list[Chunk] = []
    idx = 0

    # Sliding window over tokens while tracking page range
    # We chunk by accumulating unit tokens; when we hit size, we emit.
    window_tokens: list[int] = []
    window_text_parts: list[str] = []
    page_start = None
    page_end = None

    def emit_chunk():
        nonlocal idx, window_tokens, window_text_parts, page_start, page_end
        content = "\n\n".join(window_text_parts).strip()
        if not content:
            return
        chunks.append(
            Chunk(
                chunk_index=idx,
                page_start=page_start or 1,
                page_end=page_end or (page_start or 1),
                token_count=len(window_tokens),
                content=content,
            )
        )
        idx += 1

        # apply overlap
        if overlap_tokens > 0 and len(window_tokens) > overlap_tokens:
            overlap = window_tokens[-overlap_tokens:]
            # NOTE: We keep text overlap approximately by re-decoding overlap tokens.
            # This is good enough for Phase 1D; later we can do smarter boundary overlap.
            overlap_text = enc.decode(overlap).strip()
            window_tokens = overlap
            window_text_parts = [overlap_text] if overlap_text else []
        else:
            window_tokens = []
            window_text_parts = []
        page_start = None
        page_end = None

    for page_num, text in units:
        toks = enc.encode(text)

        if page_start is None:
            page_start = page_num
        page_end = page_num

        # If adding this unit would exceed chunk size, emit first
        if window_tokens and (len(window_tokens) + len(toks) > chunk_tokens):
            emit_chunk()
            # reset page_start for new window
            if window_tokens:
                # overlap kept some tokens; keep current page_start as this page
                page_start = page_num
            else:
                page_start = page_num

        window_tokens.extend(toks)
        window_text_parts.append(text)

        # If huge single unit, allow emit immediately
        if len(window_tokens) >= chunk_tokens:
            emit_chunk()

    # final
    if window_tokens:
        emit_chunk()

    return chunks
