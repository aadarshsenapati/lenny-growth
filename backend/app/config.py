"""
Central application configuration.

Everything an evaluator needs to change behavior (LLM provider, model names,
DB connection, retrieval params) lives here and is driven entirely by
environment variables -- no code changes required to switch providers.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    app_env: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173"
    session_secret: str = "change_me_dev_only"

    # --- LLM provider toggle ---
    # "groq"   -> cloud inference (free tier), used as the default cloud provider
    # "ollama" -> local inference, MANDATORY for the demo per assignment spec
    llm_provider: Literal["groq", "ollama"] = "groq"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"

    # --- Database (MySQL) ---
    database_url: str = "mysql+aiomysql://root:Rishi%402005@localhost:3306/lenny_growth_assistant"

    # --- Vector store (FAISS, local on disk) ---
    faiss_index_dir: str = "./data/faiss_index"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # --- Retrieval ---
    chunk_size_tokens: int = 400
    chunk_overlap_tokens: int = 60
    retrieval_top_k: int = 6
    min_similarity_score: float = 0.25  # below this, treat as "no grounding found"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
