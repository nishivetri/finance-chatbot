from __future__ import annotations

import json
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()

META_FILE = "embedding_meta.json"
LOCAL_DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _meta_path(vectorstore_dir: str) -> str:
    return os.path.join(vectorstore_dir, META_FILE)


def _openai_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings()


def _local_embeddings(model_name: str | None = None) -> HuggingFaceEmbeddings:
    name = model_name or os.getenv("HUGGINGFACE_EMBEDDING_MODEL", LOCAL_DEFAULT_MODEL)
    return HuggingFaceEmbeddings(
        model_name=name,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )


def get_provider_from_env() -> str:
    return os.getenv("EMBEDDINGS_PROVIDER", "local").strip().lower()


def build_embeddings() -> tuple[Embeddings, dict[str, Any]]:
    """
    Embeddings for ingest. Default: local HuggingFace (no OpenAI key required).
    Set EMBEDDINGS_PROVIDER=openai to use OpenAIEmbeddings.
    """
    provider = get_provider_from_env()
    if provider in ("openai", "open_ai"):
        emb = _openai_embeddings()
        meta: dict[str, Any] = {"provider": "openai", "model": "openai_default"}
    else:
        model = os.getenv("HUGGINGFACE_EMBEDDING_MODEL", LOCAL_DEFAULT_MODEL)
        emb = _local_embeddings(model)
        meta = {"provider": "local", "model": model}
    return emb, meta


def load_embeddings_for_vectorstore(vectorstore_dir: str = "vectorstore") -> Embeddings:
    """
    Must match how the index was built (metadata written next to the FAISS index).
    """
    path = _meta_path(vectorstore_dir)
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        prov = (meta.get("provider") or "local").lower()
        if prov in ("openai", "open_ai"):
            return _openai_embeddings()
        model = meta.get("model") or LOCAL_DEFAULT_MODEL
        return _local_embeddings(model)
    # Legacy indexes built before metadata: assume OpenAI
    return _openai_embeddings()


def write_embedding_meta(vectorstore_dir: str, meta: dict[str, Any]) -> None:
    os.makedirs(vectorstore_dir, exist_ok=True)
    with open(_meta_path(vectorstore_dir), "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
