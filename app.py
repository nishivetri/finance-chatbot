import os
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

load_dotenv()

app = FastAPI()

embeddings = OpenAIEmbeddings()
db = FAISS.load_local("vectorstore", embeddings)

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create a chain that retrieves and answers questions
retriever = db.as_retriever(search_kwargs={"k": 3})

class Query(BaseModel):
    question: str

@app.get("/")
def home():
    return {"message": "Finance chatbot running"}

@app.post("/ask")
def ask(query: Query):
    # Retrieve relevant documents
    docs = retriever.invoke(query.question)
    
    # Combine documents into context
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Create prompt
    prompt = f"""Use the following context to answer the question:

Context:
{context}

Question: {query.question}

Answer:"""
    
    # Get answer from LLM
    result = llm.invoke(prompt)
    answer = result.content if hasattr(result, 'content') else str(result)

    return {
        "answer": answer,
        "sources": [
            doc.metadata.get("source", "unknown")
            for doc in docs
        ]
    }

