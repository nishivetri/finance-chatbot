from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

load_dotenv()


def resolve_llm_provider() -> str:
    """
    If LLM_PROVIDER is unset, pick the first matching credential:
    groq (GROQ_API_KEY) -> google (GOOGLE_API_KEY/GEMINI_API_KEY) -> openai (OPENAI_API_KEY) -> ollama (local).
    """
    raw = os.getenv("LLM_PROVIDER", "").strip().lower()
    if raw:
        mapping = {
            "openai": "openai",
            "oai": "openai",
            "groq": "groq",
            "google": "google",
            "gemini": "google",
            "genai": "google",
            "ollama": "ollama",
            "local": "ollama",
        }
        if raw not in mapping:
            raise ValueError(
                f"Unknown LLM_PROVIDER={raw!r}. Use: openai, groq, google, ollama (or leave unset for auto)."
            )
        return mapping[raw]
    if os.getenv("GROQ_API_KEY"):
        return "groq"
    if os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"):
        return "google"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "ollama"


def get_chat_llm() -> BaseChatModel:
    p = resolve_llm_provider()
    if p == "groq":
        from langchain_groq import ChatGroq

        return ChatGroq(
            model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
            temperature=0,
        )
    if p == "google":
        from langchain_google_genai import ChatGoogleGenerativeAI

        return ChatGoogleGenerativeAI(
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            temperature=0,
        )
    if p == "ollama":
        from langchain_community.chat_models import ChatOllama

        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
            temperature=0,
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
    )


def active_llm_label() -> str:
    p = resolve_llm_provider()
    if p == "groq":
        return f"groq / {os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')}"
    if p == "google":
        return f"google / {os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')}"
    if p == "ollama":
        return f"ollama / {os.getenv('OLLAMA_MODEL', 'llama3.2')} @ {os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')}"
    return f"openai / {os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}"
