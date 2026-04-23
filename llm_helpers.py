"""User-facing messages for LLM failures (Streamlit + API)."""


def llm_error_message(exc: BaseException) -> str:
    text = str(exc).lower()
    raw = str(exc)
    if "insufficient_quota" in text or ("429" in raw and "quota" in text):
        return (
            "OpenAI reports **no quota / billing** (HTTP 429). Switch to another provider in `.env` "
            "(e.g. `LLM_PROVIDER=groq` + `GROQ_API_KEY`, or `LLM_PROVIDER=google` + `GOOGLE_API_KEY`), "
            "or add billing: https://platform.openai.com/account/billing"
        )
    if "401" in raw or "invalid_api_key" in text or "invalid api key" in text:
        return (
            "Invalid or rejected API key (HTTP 401). Check the key for your active `LLM_PROVIDER` "
            "in `.env` (Groq: `GROQ_API_KEY`, Google: `GOOGLE_API_KEY`, OpenAI: `OPENAI_API_KEY`)."
        )
    if "403" in raw and ("permission" in text or "forbidden" in text):
        return (
            "API returned 403 (forbidden). Check that the key is enabled for this model and region."
        )
    if "connection" in text and ("refused" in text or "ollama" in text):
        return (
            "**Ollama** is not reachable. Install from https://ollama.com , run `ollama serve`, "
            "and `ollama pull llama3.2` (or set `OLLAMA_MODEL` to a model you have)."
        )
    if "rate limit" in text and "quota" not in text:
        return (
            "Rate limit from the provider. Wait and retry, or try another `LLM_PROVIDER` in `.env`."
        )
    return raw
