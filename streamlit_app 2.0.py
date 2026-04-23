import os
import sys
import subprocess
from dotenv import load_dotenv

import streamlit as st

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

load_dotenv()

st.set_page_config(page_title="Finance Chatbot", layout="wide")

st.title("Finance Chatbot")

DATA_DIR = "vectorstore"

@st.cache_resource
def load_qa():
    embeddings = OpenAIEmbeddings()
    if not os.path.exists(DATA_DIR):
        return None
    db = FAISS.load_local(DATA_DIR, embeddings)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
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
        st.success("Ingestion finished. Reloading index...")
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
    st.markdown("Ensure `OPENAI_API_KEY` is set in the environment or `.env` file.")

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
                st.error(f"Error running QA: {e}")
