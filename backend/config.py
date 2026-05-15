from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # LLM
    model_path: str = "./models/gemma-2-2b-it-Q4_K_M.gguf"
    llm_backend: str = "local"
    llm_api_url: str = "http://localhost:8080/v1"
    model_ctx: int = 4096
    model_threads: int = 8
    max_answer_tokens: int = 512

    # Gemini fallback
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"

    # HuggingFace
    hf_token: str = ""

    # ChromaDB
    chroma_path: str = "./chroma_db"
    chroma_host: str = "localhost"
    chroma_port: int = 8002

    # Embedding
    embedding_model: str = "BAAI/bge-small-en-v1.5"

    # FastAPI
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # RAG
    top_k_retrieval: int = 6
    confidence_threshold: float = 0.45

    @property
    def uploads_dir(self) -> Path:
        p = Path("./uploads")
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def models_dir(self) -> Path:
        p = Path("./models")
        p.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache
def get_settings() -> Settings:
    return Settings()
