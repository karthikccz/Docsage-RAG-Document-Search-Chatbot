"""
Hybrid retrieval: Chroma (dense/semantic) + BM25 (sparse/keyword)
combined via Reciprocal Rank Fusion (RRF).

Why hybrid?
  - Dense search finds semantically similar chunks even with different wording.
  - Sparse BM25 catches exact keyword matches dense search can miss.
  - RRF merges both ranked lists without needing to tune score weights.
"""

import os
import json
import math
from typing import List, Optional

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from .config import settings

# ── Embedding model (loaded once per process) ─────────────────────────────────
_embeddings = HuggingFaceEmbeddings(model_name=settings.embedding_model)

PERSIST_DIR   = settings.vector_store_dir
REGISTRY_PATH = os.path.join(PERSIST_DIR, "registry.json")
CORPUS_PATH   = os.path.join(PERSIST_DIR, "bm25_corpus.json")

_store: Optional[Chroma] = None
_bm25:  Optional[BM25Okapi] = None
_corpus: List[Document] = []   # parallel list to the BM25 index


# ── Internal helpers ───────────────────────────────────────────────────────────

def _get_store() -> Chroma:
    global _store
    if _store is None:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _store = Chroma(
            collection_name="documents",
            embedding_function=_embeddings,
            persist_directory=PERSIST_DIR,
        )
    return _store


def _load_corpus() -> List[Document]:
    """Load the BM25 corpus from disk (persisted as JSON beside the Chroma index)."""
    if not os.path.exists(CORPUS_PATH):
        return []
    with open(CORPUS_PATH) as f:
        raw = json.load(f)
    return [Document(page_content=r["text"], metadata=r["meta"]) for r in raw]


def _save_corpus(docs: List[Document]) -> None:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    with open(CORPUS_PATH, "w") as f:
        json.dump([{"text": d.page_content, "meta": d.metadata} for d in docs], f)


def _build_bm25(docs: List[Document]) -> Optional[BM25Okapi]:
    if not docs:
        return None
    tokenized = [d.page_content.lower().split() for d in docs]
    return BM25Okapi(tokenized)


def _ensure_bm25():
    """Lazy-load BM25 index from disk on first use."""
    global _bm25, _corpus
    if _bm25 is None:
        _corpus = _load_corpus()
        _bm25   = _build_bm25(_corpus)


def _load_registry() -> dict:
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {}


def _save_registry(registry: dict) -> None:
    os.makedirs(PERSIST_DIR, exist_ok=True)
    with open(REGISTRY_PATH, "w") as f:
        json.dump(registry, f, indent=2)


# ── RRF fusion ────────────────────────────────────────────────────────────────

def _rrf(
    dense_hits: List[Document],
    sparse_hits: List[Document],
    k: int = 60,
) -> List[Document]:
    """
    Reciprocal Rank Fusion merges two ranked lists into one without
    needing to normalise or compare raw scores across different systems.

    Score for a document d = Σ 1 / (k + rank(d))
    where rank is 1-indexed position in each list.
    k=60 is the standard default from the original RRF paper.
    """
    scores: dict[str, float]   = {}
    docs_by_id: dict[str, Document] = {}

    for rank, doc in enumerate(dense_hits, start=1):
        uid = doc.page_content[:120]           # use content prefix as dedup key
        scores[uid]    = scores.get(uid, 0) + 1 / (k + rank)
        docs_by_id[uid] = doc

    for rank, doc in enumerate(sparse_hits, start=1):
        uid = doc.page_content[:120]
        scores[uid]    = scores.get(uid, 0) + 1 / (k + rank)
        docs_by_id[uid] = doc

    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [docs_by_id[uid] for uid, _ in ranked]


# ── Public API ─────────────────────────────────────────────────────────────────

def add_documents(chunks: List[Document], doc_id: str, filename: str) -> int:
    global _bm25, _corpus

    # 1. Dense store
    _get_store().add_documents(chunks)

    # 2. Sparse corpus
    _ensure_bm25()
    _corpus.extend(chunks)
    _save_corpus(_corpus)
    _bm25 = _build_bm25(_corpus)

    # 3. Registry
    registry = _load_registry()
    registry[doc_id] = {"filename": filename, "chunks": len(chunks)}
    _save_registry(registry)

    return len(chunks)


def hybrid_search(
    query: str,
    doc_id: Optional[str] = None,
    dense_k: int = None,
    sparse_k: int = None,
) -> List[Document]:
    """
    Returns a fused ranked list of documents via RRF.
    Optionally filtered to a single doc_id.
    """
    dense_k  = dense_k  or settings.dense_top_k
    sparse_k = sparse_k or settings.sparse_top_k

    if not _load_registry():
        return []

    # ── Dense (Chroma) ──────────────────────────────────────────────────────
    store = _get_store()
    search_kwargs = {"k": dense_k}
    if doc_id:
        search_kwargs["filter"] = {"doc_id": doc_id}
    dense_hits = store.similarity_search(query, **search_kwargs)

    # ── Sparse (BM25) ───────────────────────────────────────────────────────
    _ensure_bm25()
    sparse_hits: List[Document] = []
    if _bm25 and _corpus:
        tokens  = query.lower().split()
        scores  = _bm25.get_scores(tokens)
        # sort all corpus indices by BM25 score, take top sparse_k
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        for idx, score in indexed[:sparse_k * 3]:   # over-fetch before filter
            if score <= 0:
                break
            doc = _corpus[idx]
            if doc_id and doc.metadata.get("doc_id") != doc_id:
                continue
            sparse_hits.append(doc)
            if len(sparse_hits) >= sparse_k:
                break

    # ── RRF fusion ──────────────────────────────────────────────────────────
    return _rrf(dense_hits, sparse_hits)


def get_retriever(doc_id: Optional[str] = None, k: int = 4):
    """
    LangChain-compatible retriever shim used by rag_chain.
    Wraps hybrid_search so the chain interface stays unchanged.
    """
    if not _load_registry():
        return None

    class HybridRetriever:
        def invoke(self, query: str) -> List[Document]:
            return hybrid_search(query, doc_id=doc_id)[: k]

    return HybridRetriever()


def list_documents() -> List[dict]:
    registry = _load_registry()
    return [{"doc_id": doc_id, **meta} for doc_id, meta in registry.items()]
