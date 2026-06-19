import os
import json
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from .config import settings

# Loaded once per process. First call downloads ~90MB of model weights from
# Hugging Face and caches them locally -- no API key, no per-call cost.
_embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)

PERSIST_DIR = settings.vector_store_dir
REGISTRY_PATH = os.path.join(PERSIST_DIR, "registry.json")

_store: Optional[Chroma] = None


def _get_store() -> Chroma:
    """
    Chroma persists to disk as it writes -- unlike FAISS there's no explicit
    save_local()/load_local() step. Pointing two Chroma instances at the same
    persist_directory (e.g. across a server restart) just works.
    """
    global _store
    if _store is None:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _store = Chroma(
            collection_name="documents",
            embedding_function=_embeddings,
            persist_directory=PERSIST_DIR,
        )
    return _store


def _load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {}


def _save_registry(registry: dict) -> None:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


def add_documents(chunks: List[Document], doc_id: str, filename: str) -> int:
    """Embed a fresh batch of chunks and write them into the Chroma collection."""
    store = _get_store()
    store.add_documents(chunks)

    registry = _load_registry()
    registry[doc_id] = {"filename": filename, "chunks": len(chunks)}
    _save_registry(registry)

    return len(chunks)


def get_retriever(doc_id: Optional[str] = None, k: int = 4):
    """Return a LangChain retriever, optionally scoped to a single document."""
    if not _load_registry():
        return None  # nothing has ever been indexed

    store = _get_store()
    search_kwargs = {"k": k}
    if doc_id:
        search_kwargs["filter"] = {"doc_id": doc_id}
    return store.as_retriever(search_kwargs=search_kwargs)


def list_documents() -> List[dict]:
    registry = _load_registry()
    return [{"doc_id": doc_id, **meta} for doc_id, meta in registry.items()]
