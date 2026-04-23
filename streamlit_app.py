import os
import sys
import subprocess
from dotenv import load_dotenv

import streamlit as st

from langchain_community.vectorstores import FAISS

from embedding_config import load_embeddings_for_vectorstore
from llm_factory import active_llm_label, get_chat_llm
from llm_helpers import llm_error_message

load_dotenv()

st.set_page_config(page_title="Finance Chatbot", layout="wide")

st.title("Finance Chatbot")

DATA_DIR = "vectorstore"

@st.cache_resource
def load_qa():
    if not os.path.exists(DATA_DIR):
        return None
    embeddings = load_embeddings_for_vectorstore(DATA_DIR)
    db = FAISS.load_local(
        DATA_DIR, embeddings, allow_dangerous_deserialization=True
    )
    llm = get_chat_llm()
    
    retriever = db.as_retriever(search_kwargs={"k": 3})
    
    return {
        "llm": llm,
        "retriever": retriever
    }

def build_index():
    # Run the ingestion script in a subprocess so we don't re-import top-level code
    st.info("Running ingestion to (re)build vectorstore. This can take a while...")
    try:
        subprocess.run([sys.executable, "ingest.py"], check=True)
        st.cache_resource.clear()
        st.success("Ingestion finished. Reloading index...")
        st.rerun()
    except subprocess.CalledProcessError as e:
        st.error(f"Ingestion failed: {e}")


with st.sidebar:
    st.header("Index / Controls")
    if not os.path.exists(DATA_DIR):
        st.warning("No vectorstore found. Click to build the index from `data/`.")
        if st.button("Build index now"):
            build_index()
    else:
        st.success("Vectorstore found")
        if st.button("Rebuild index"):
            build_index()
    st.markdown("---")
    st.markdown(
        "**Answers (LLM):** set one of: `GROQ_API_KEY` ([Groq console](https://console.groq.com/keys)), "
        "`GOOGLE_API_KEY` ([AI Studio](https://aistudio.google.com/apikey)), or `OPENAI_API_KEY`. "
        "Optional: `LLM_PROVIDER` = `groq` | `google` | `openai` | `ollama`. "
        "If unset, the first available key above is used (Groq before OpenAI). "
        "**Local [Ollama](https://ollama.com):** no cloud key; install and `ollama pull llama3.2`."
    )
    st.caption(f"Active chat: `{active_llm_label()}`")

qa_components = load_qa()

if qa_components is None:
    st.error("No QA chain available. Build the index first via the sidebar or run `python ingest.py`.")
else:
    query = st.text_input("Ask a question about the ingested finance documents:")
    if st.button("Ask") and query:
        with st.spinner("Thinking..."):
            try:
                llm = qa_components["llm"]
                retriever = qa_components["retriever"]
                
                # Retrieve relevant documents
                docs = retriever.invoke(query)
                
                # Combine documents into context
                context = "\n\n".join([doc.page_content for doc in docs])
                
                # Create prompt
                prompt = f"""Use the following context to answer the question:

Context:
{context}

Question: {query}

Answer:"""
                
                # Get answer from LLM
                result = llm.invoke(prompt)
                answer = result.content if hasattr(result, 'content') else str(result)
                
                st.subheader("Answer")
                st.write(answer)
                
                if docs:
                    st.subheader("Sources")
                    for doc in docs:
                        st.write(doc.metadata.get("source", "unknown"))
                        
            except Exception as e:
                st.markdown(llm_error_message(e))
                with st.expander("Technical details"):
                    st.code(str(e))
