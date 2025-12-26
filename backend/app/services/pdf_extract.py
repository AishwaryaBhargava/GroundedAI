import re
import fitz  # PyMuPDF


def _normalize_text(s: str) -> str:
    s = s.replace("\u00ad", "")  # soft hyphen
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def extract_pages(pdf_bytes: bytes) -> list[dict]:
    """
    Returns list of:
    { "page": 1-based page number, "text": cleaned_text }
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        pages.append({"page": i + 1, "raw": text})

    # Detect repeated header/footer lines (very common in PDFs)
    # Heuristic: top line + bottom line repeated in >= 50% pages
    top_counts = {}
    bot_counts = {}

    def first_nonempty_line(t: str) -> str | None:
        for line in t.splitlines():
            line = line.strip()
            if line:
                return line
        return None

    def last_nonempty_line(t: str) -> str | None:
        for line in reversed(t.splitlines()):
            line = line.strip()
            if line:
                return line
        return None

    tops = []
    bots = []
    for p in pages:
        top = first_nonempty_line(p["raw"])
        bot = last_nonempty_line(p["raw"])
        tops.append(top)
        bots.append(bot)
        if top:
            top_counts[top] = top_counts.get(top, 0) + 1
        if bot:
            bot_counts[bot] = bot_counts.get(bot, 0) + 1

    threshold = max(2, len(pages) // 2)
    common_tops = {k for k, v in top_counts.items() if v >= threshold}
    common_bots = {k for k, v in bot_counts.items() if v >= threshold}

    cleaned_pages = []
    for p in pages:
        lines = [ln.rstrip() for ln in (p["raw"] or "").splitlines()]

        # Remove common header/footer lines
        if lines and lines[0].strip() in common_tops:
            lines = lines[1:]
        if lines and lines[-1].strip() in common_bots:
            lines = lines[:-1]

        # Remove lines that are ONLY page numbers
        lines = [ln for ln in lines if not re.fullmatch(r"\s*\d+\s*", ln)]

        text = _normalize_text("\n".join(lines))
        cleaned_pages.append({"page": p["page"], "text": text})

    return cleaned_pages
