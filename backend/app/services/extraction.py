from typing import List
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractedDocument:
    pages: List[str]
    detected_type: str


def extract_document(
    file_bytes: bytes,
    content_type: str,
    filename: str | None = None,
) -> ExtractedDocument:
    """
    6A-1 Extraction interface.

    Supported:
    - PDF
    - TXT
    - DOCX
    - PPTX

    Contract:
    - pages: list of {"page": int, "text": str}
    - detected_type: lowercase string
    """

    # ---- PDF ----
    if content_type == "application/pdf" or (
        filename and filename.lower().endswith(".pdf")
    ):
        from app.services.pdf_extract import extract_pages

        pages = extract_pages(file_bytes)
        return ExtractedDocument(pages=pages, detected_type="pdf")

    # ---- TXT ----
    if content_type == "text/plain" or (
        filename and filename.lower().endswith(".txt")
    ):
        from app.services.txt_extract import extract_pages

        pages = extract_pages(file_bytes)
        return ExtractedDocument(pages=pages, detected_type="txt")
    
    # ---- DOCX ----
    if content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or (
        filename and filename.lower().endswith(".docx")
    ):
        from app.services.docx_extract import extract_pages

        pages = extract_pages(file_bytes)
        return ExtractedDocument(pages=pages, detected_type="docx")

    # ---- PPTX ----
    if content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation" or (
        filename and filename.lower().endswith(".pptx")
    ):
        from app.services.pptx_extract import extract_pages
        pages = extract_pages(file_bytes)
        return ExtractedDocument(pages=pages, detected_type="pptx")

    # ---- CSV ----
    if content_type == "text/csv" or (
        filename and filename.lower().endswith(".csv")
    ):
        from app.services.csv_extract import extract_pages
        pages = extract_pages(file_bytes)
        return ExtractedDocument(pages=pages, detected_type="csv")

    # ---- Unsupported ----
    raise ValueError("Unsupported document type")
