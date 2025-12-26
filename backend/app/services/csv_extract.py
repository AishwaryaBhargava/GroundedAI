# app/services/csv_extract.py

import csv
import io
from typing import List, Dict


def extract_pages(
    csv_bytes: bytes,
    rows_per_page: int = 50,
) -> List[Dict]:
    """
    Extract CSV into pseudo-pages.

    Each page is:
    {
      "page": <int>,
      "text": <str>
    }
    """

    text = csv_bytes.decode("utf-8", errors="ignore")
    reader = csv.reader(io.StringIO(text))

    rows = list(reader)
    if not rows:
        return []

    header = rows[0]
    data_rows = rows[1:]

    pages: List[Dict] = []
    page_num = 1

    for i in range(0, len(data_rows), rows_per_page):
        chunk = data_rows[i : i + rows_per_page]

        lines = []
        lines.append(" | ".join(header))
        lines.append("-" * 40)

        for row in chunk:
            padded = row + [""] * (len(header) - len(row))
            lines.append(" | ".join(padded))

        page_text = "\n".join(lines).strip()
        if page_text:
            pages.append(
                {
                    "page": page_num,
                    "text": page_text,
                }
            )
            page_num += 1

    return pages
