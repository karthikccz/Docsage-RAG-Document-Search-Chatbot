from typing import List, Optional, Tuple

from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from .config import settings
from .vector_store import get_retriever

SYSTEM_PROMPT = """You are a precise research assistant. Answer the question using \
ONLY the context below, which was retrieved from the user's own uploaded documents. \
If the context doesn't contain the answer, say plainly that the uploaded documents \
don't cover it -- never guess or invent details.

Context:
{context}
"""

_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ]
)

# Talks to a local Ollama server -- no API key, no per-token cost. Requires
# Ollama installed and the model pulled once: `ollama pull llama3.2`.
_llm = ChatOllama(
    model=settings.ollama_model,
    base_url=settings.ollama_base_url,
    temperature=0.2,
)

_chain = _prompt | _llm | StrOutputParser()


def _format_docs(docs) -> str:
    return "\n\n".join(
        f"[Source: {d.metadata.get('filename')}, p.{d.metadata.get('page')}]\n{d.page_content}"
        for d in docs
    )


def answer_question(question: str, doc_id: Optional[str] = None) -> Tuple[str, List[dict]]:
    retriever = get_retriever(doc_id=doc_id)
    if retriever is None:
        return "No documents have been indexed yet. Upload a PDF first.", []

    docs = retriever.invoke(question)
    if not docs:
        return "I couldn't find anything relevant in the uploaded documents.", []

    context = _format_docs(docs)

    try:
        answer = _chain.invoke({"context": context, "question": question})
    except Exception as exc:
        # The most common failure here is "Ollama isn't running" or "the model
        # hasn't been pulled yet" -- surface something actionable instead of a 500.
        return (
            f"Couldn't reach the local Ollama model '{settings.ollama_model}'. "
            f"Make sure Ollama is running and you've run "
            f"`ollama pull {settings.ollama_model}`. (Details: {exc})",
            [],
        )

    sources = [
        {
            "content": d.page_content[:300],
            "page": d.metadata.get("page"),
            "doc_id": d.metadata.get("doc_id"),
            "filename": d.metadata.get("filename"),
        }
        for d in docs
    ]
    return answer, sources
