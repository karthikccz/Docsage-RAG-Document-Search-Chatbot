from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- AI: fully local & free ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    reranker_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Retrieval ---
    chunk_size: int = 1000
    chunk_overlap: int = 150
    dense_top_k: int = 10      # candidates from Chroma (semantic)
    sparse_top_k: int = 10     # candidates from BM25  (keyword)
    rerank_top_n: int = 4      # final chunks sent to LLM after reranking

    # --- Storage ---
    vector_store_dir: str = "storage/vector_store"
    upload_dir: str = "storage/uploads"

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
