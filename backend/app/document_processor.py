import os
import uuid
from typing import List, Tuple

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from .config import settings


def save_upload(file_bytes: bytes, filename: str) -> Tuple[str, str]:
    """Persist the raw upload to disk and hand back a unique doc_id + path."""
    doc_id = uuid.uuid4().hex[:12]
    os.makedirs(settings.upload_dir, exist_ok=True)
    safe_name = filename.replace("/", "_").replace("\\", "_")
    path = os.path.join(settings.upload_dir, f"{doc_id}_{safe_name}")
    with open(path, "wb") as f:
        f.write(file_bytes)
    return doc_id, path


def load_and_chunk(path: str, doc_id: str, filename: str) -> List[Document]:
    """
    Turn a PDF on disk into a list of LangChain Documents, one per chunk,
    each tagged with metadata we'll need later for filtering and citations.
    """
    loader = PyPDFLoader(path)
    pages = loader.load()  # one Document per PDF page; metadata already has "page"

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)

    for chunk in chunks:
        chunk.metadata["doc_id"] = doc_id
        chunk.metadata["filename"] = filename
        # PyPDFLoader's "page" is 0-indexed; show humans 1-indexed page numbers
        chunk.metadata["page"] = chunk.metadata.get("page", 0) + 1

    return chunks
