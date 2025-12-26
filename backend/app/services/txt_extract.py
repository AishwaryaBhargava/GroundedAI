import re
from typing import List


def _normalize_text(text: str) -> str:
    """
    Normalize plain text:
    - remove weird whitespace
    - collapse multiple spaces
    - collapse excessive newlines
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pages(
    file_bytes: bytes,
    *,
    chars_per_page: int = 2000,
) -> List[dict]:
    """
    Extract pseudo-pages from a TXT file.

    Returns list of:
    {
        "page": 1-based page number,
        "text": cleaned_text
    }

    This mirrors pdf_extract.extract_pages exactly in shape.
    """

    try:
        raw_text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        # Fallback for messy text files
        raw_text = file_bytes.decode("latin-1", errors="ignore")

    normalized = _normalize_text(raw_text)

    if not normalized:
        return []

    pages = []
    page_num = 1

    for i in range(0, len(normalized), chars_per_page):
        chunk = normalized[i : i + chars_per_page].strip()
        if not chunk:
            continue

        pages.append(
            {
                "page": page_num,
                "text": chunk,
            }
        )
        page_num += 1

    return pages
