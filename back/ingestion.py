from dataclasses import asdict, dataclass
from io import BytesIO
from pathlib import Path
import re
from typing import Any

import pymupdf


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str
    word_count: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def clean_text(text: str) -> str:
    """Normalize whitespace """
    text = text.replace("\u00ad", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_into_chunks(
    text: str,
    chunk_size: int = 450,
    overlap: int = 75,
) -> list[str]:
    """
    Split text into overlapping word-based chunks.

    chunk_size=450 gives chunks approximately between 300 and 600
    words for normal prose. Very short pages will naturally produce
    smaller chunks.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and smaller than chunk_size")

    words = text.split()

    if not words:
        return []

    chunks = []
    step = chunk_size - overlap

    for start in range(0, len(words), step):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])

        if chunk:
            chunks.append(chunk)

        if end == len(words):
            break

    return chunks


def extract_pdf_chunks(
    pdf_bytes: bytes,
    filename: str,
    document_id: str,
    chunk_size: int = 450,
    overlap: int = 75,
) -> list[Chunk]:
    """
    Extract a PDF page by page and create chunks within each page.

    Page numbers returned to users are one-based.
    """
    chunks: list[Chunk] = []

    try:
        document = pymupdf.open(
            stream=BytesIO(pdf_bytes),
            filetype="pdf",
        )
    except Exception as exc:
        raise ValueError("The uploaded file is not a valid PDF") from exc

    try:
        for page_index, page in enumerate(document):
            page_number = page_index + 1

            raw_text = page.get_text("text", sort=True)
            page_text = clean_text(raw_text)

            if not page_text:
                continue

            page_chunks = split_into_chunks(
                page_text,
                chunk_size=chunk_size,
                overlap=overlap,
            )

            for chunk_index, chunk_text in enumerate(page_chunks):
                chunk_id = (
                    f"{document_id}-page-{page_number}-chunk-{chunk_index}"
                )

                chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        document_id=document_id,
                        filename=filename,
                        page_number=page_number,
                        text=chunk_text,
                        word_count=len(chunk_text.split()),
                    )
                )
    finally:
        document.close()

    return chunks