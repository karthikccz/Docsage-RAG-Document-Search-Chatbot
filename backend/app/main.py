from typing import List

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .schemas import UploadResponse, ChatRequest, ChatResponse, DocumentInfo
from .document_processor import save_upload, load_and_chunk
from .vector_store import add_documents, list_documents
from .rag_chain import answer_question

app = FastAPI(title="RAG Document Search API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported right now.")

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "The uploaded file is empty.")

    doc_id, path = save_upload(file_bytes, file.filename)
    chunks = load_and_chunk(path, doc_id, file.filename)

    if not chunks:
        raise HTTPException(422, "No extractable text was found in this PDF.")

    count = add_documents(chunks, doc_id, file.filename)
    return UploadResponse(doc_id=doc_id, filename=file.filename, chunks_indexed=count)


@app.get("/api/documents", response_model=List[DocumentInfo])
def get_documents():
    return list_documents()


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    answer, sources = answer_question(req.question, req.doc_id)
    return ChatResponse(answer=answer, sources=sources)
