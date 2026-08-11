from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from .ingestion import extract_pdf_chunks

app = FastAPI(title="DocSearch AI")

# Temporary in-memory storage for the first version.
# It will be replaced by SQLite or Supabase later.
DOCUMENTS: dict[str, dict] = {}
CHUNKS: list[dict] = []

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is missing",
        )

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported",
        )

    pdf_bytes = await file.read()

    if not pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty",
        )

    # Keep this limit small during development.
    max_size = 10 * 1024 * 1024

    if len(pdf_bytes) > max_size:
        raise HTTPException(
            status_code=413,
            detail="PDF must be smaller than 10 MB",
        )

    document_id = uuid4().hex

    try:
        chunks = extract_pdf_chunks(
            pdf_bytes=pdf_bytes,
            filename=file.filename,
            document_id=document_id,
            chunk_size=450,
            overlap=75,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail=(
                "No selectable text was found. "
                "This may be a scanned PDF requiring OCR."
            ),
        )

    chunk_dicts = [chunk.to_dict() for chunk in chunks]

    DOCUMENTS[document_id] = {
        "document_id": document_id,
        "filename": file.filename,
        "chunk_count": len(chunk_dicts),
    }

    CHUNKS.extend(chunk_dicts)

    return {
        "document_id": document_id,
        "filename": file.filename,
        "chunks_created": len(chunk_dicts),
        "sample_chunk": chunk_dicts[0],
    }