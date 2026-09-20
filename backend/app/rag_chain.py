"""
RAG chain with reranking.

Pipeline:
  question
    → hybrid_search (Chroma dense + BM25 sparse, fused via RRF)   ← vector_store.py
    → CrossEncoder reranker (scores every chunk vs the question)
    → top-N chunks stuffed into prompt
    → Ollama LLM
    → answer + source citations
"""

from typing import List, Optional, Tuple

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from sentence_transformers import CrossEncoder

from .config import settings
from .vector_store import hybrid_search

# ── Models (loaded once per process) ─────────────────────────────────────────

# CrossEncoder: given (query, passage) pairs, outputs a relevance score.
# More accurate than cosine similarity but slower — used AFTER the fast
# initial retrieval to re-order the candidate set.
_reranker = CrossEncoder(settings.reranker_model)

_llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.2,
)

SYSTEM_PROMPT = """You are a precise research assistant. Answer the question using \
ONLY the context below, which was retrieved from the user's own uploaded documents. \
If the context doesn't contain the answer, say plainly that the uploaded documents \
don't cover it -- never guess or invent details.

Context:
{context}
"""

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])

_chain = _prompt | _llm | StrOutputParser()


# ── Reranker ──────────────────────────────────────────────────────────────────

def _rerank(query: str, docs, top_n: int):
    """
    Score every (query, chunk) pair with the cross-encoder.
    Returns the top_n chunks sorted by relevance score descending.

    CrossEncoder reads the query and passage *together*, giving it much
    richer context than cosine similarity which compares them independently.
    """
    if not docs:
        return []
    pairs  = [(query, d.page_content) for d in docs]
    scores = _reranker.predict(pairs)          # list of floats, one per pair
    ranked = sorted(zip(scores, docs), key=lambda x: x[0], reverse=True)
    return [doc for _, doc in ranked[:top_n]]


# ── Format context block ──────────────────────────────────────────────────────

def _format_docs(docs) -> str:
    return "\n\n".join(
        f"[Source: {d.metadata.get('filename')}, p.{d.metadata.get('page')}]\n{d.page_content}"
        for d in docs
    )


# ── Public entry point ────────────────────────────────────────────────────────

def answer_question(
    question: str,
    doc_id: Optional[str] = None,
) -> Tuple[str, List[dict]]:
    # 1. Hybrid retrieval (dense + sparse → RRF)
    candidates = hybrid_search(
        question,
        doc_id=doc_id,
        dense_k=settings.dense_top_k,
        sparse_k=settings.sparse_top_k,
    )

    if not candidates:
        return "No documents have been indexed yet. Upload a PDF first.", []

    # 2. Rerank candidates, keep top N for the prompt
    docs = _rerank(question, candidates, top_n=settings.rerank_top_n)

    if not docs:
        return "I couldn't find anything relevant in the uploaded documents.", []

    # 3. Build context + call LLM
    context = _format_docs(docs)
    try:
        answer = _chain.invoke({"context": context, "question": question})
    except Exception as exc:
        return (
            f"Couldn't reach the local Ollama model '{settings.ollama_model}'. "
            f"Make sure Ollama is running and you've run "
            f"`ollama pull {settings.ollama_model}`. (Details: {exc})",
            [],
        )

    sources = [
        {
            "content":  d.page_content[:300],
            "page":     d.metadata.get("page"),
            "doc_id":   d.metadata.get("doc_id"),
            "filename": d.metadata.get("filename"),
        }
        for d in docs
    ]
    return answer, sources
