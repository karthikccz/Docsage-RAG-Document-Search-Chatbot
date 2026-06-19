from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- AI: fully local & free, no API keys, no billing ---
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # --- Chunking ---
    chunk_size: int = 1000
    chunk_overlap: int = 150

    # --- Storage ---
    vector_store_dir: str = "storage/vector_store"
    upload_dir: str = "storage/uploads"

    # --- CORS ---
    allowed_origins: str = "http://localhost:5173"

    class Config:
        env_file = ".env"


settings = Settings()
