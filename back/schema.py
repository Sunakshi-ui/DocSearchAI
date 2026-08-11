from pydantic import BaseModel

class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    text: str

class SearchResult(ChunkMetadata):
    score: float

class UploadResponse(BaseModel):
    document_id: str
    filename: str
    pages: int
    chunks_created: int