from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from langchain_community.vectorstores import FAISS
from langchain_core.language_models.chat_models import BaseChatModel

from embedding_config import load_embeddings_for_vectorstore
from llm_factory import get_chat_llm
from llm_helpers import llm_error_message

load_dotenv()

app = FastAPI()

db = None
retriever = None
llm: BaseChatModel | None = None
_ready = False
_load_error: str | None = None


def _vectorstore_ready() -> bool:
    idx = os.path.join("vectorstore", "index.faiss")
    return os.path.isfile(idx)


@app.on_event("startup")
def _startup() -> None:
    global db, retriever, llm, _ready, _load_error
    if not _vectorstore_ready():
        _load_error = "No vectorstore (run python ingest.py first)."
        return
    try:
        embeddings = load_embeddings_for_vectorstore("vectorstore")
        db = FAISS.load_local(
            "vectorstore", embeddings, allow_dangerous_deserialization=True
        )
        llm = get_chat_llm()
        retriever = db.as_retriever(search_kwargs={"k": 3})
        _ready = True
    except Exception as e:  # noqa: BLE001
        _load_error = str(e)


class Query(BaseModel):
    question: str


@app.get("/")
def home() -> dict[str, Any]:
    if not _ready:
        return {
            "message": "Finance chatbot — vectorstore not ready",
            "ok": False,
            "detail": _load_error,
        }
    return {"message": "Finance chatbot running", "ok": True}


@app.post("/ask")
def ask(query: Query) -> dict[str, Any]:
    if not _ready or retriever is None or llm is None:
        raise HTTPException(
            status_code=503,
            detail=_load_error or "Vectorstore or model not available",
        )
    docs = retriever.invoke(query.question)
    context = "\n\n".join([doc.page_content for doc in docs])
    prompt = f"""Use the following context to answer the question:

Context:
{context}

Question: {query.question}

Answer:"""
    try:
        result = llm.invoke(prompt)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"{llm_error_message(e)} (raw: {e!s})",
        ) from e
    answer = result.content if hasattr(result, "content") else str(result)
    return {
        "answer": answer,
        "sources": [doc.metadata.get("source", "unknown") for doc in docs],
    }
