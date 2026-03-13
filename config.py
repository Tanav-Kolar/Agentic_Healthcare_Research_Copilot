"""Centralised application configuration loaded from environment / .env file."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings

# ──────────────────────────────────────────────
# Resolve project root (one level up from this file)
# ──────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """All configuration values — populated from env vars or .env file."""

    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "gemma3:12b"
    ollama_timeout: int = 600  # 10 minutes for local inference

    # ── Qdrant ──
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "pubmed_articles"

    # ── PubMed E-utilities ──
    ncbi_api_key: str = ""
    ncbi_email: str = ""

    # ── Embedding model ──
    embedding_model: str = (
        "microsoft/BiomedNLP-BiomedBERT-base-uncased-abstract-fulltext"
    )

    # ── App ──
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"

    model_config = {
        "env_file": str(PROJECT_ROOT / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# Singleton — import this everywhere
settings = Settings()
