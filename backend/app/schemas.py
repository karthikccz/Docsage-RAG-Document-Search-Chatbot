from typing import List, Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    doc_id: str
    filename: str
    chunks_indexed: int


class SourceChunk(BaseModel):
    content: str
    page: Optional[int] = None
    doc_id: str
    filename: str


class ChatRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None  # None -> search across every indexed document


class ChatResponse(BaseModel):
    answer: str
    sources: List[SourceChunk]


class DocumentInfo(BaseModel):
    doc_id: str
    filename: str
    chunks: int
