import os
import fitz  # PyMuPDF
import docx2txt
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS

DATA_PATH = "data"

def load_pdf(path: str):
    try:
        doc = fitz.open(path)
        texts = []
        for page in doc:
            texts.append(page.get_text())
        return "\n\n".join(texts)
    except Exception as e:
        print(f"Failed to load PDF {path}: {e}")
        return ""

def load_docx(path: str):
    try:
        text = docx2txt.process(path)
        return text or ""
    except Exception as e:
        print(f"Failed to load DOCX {path}: {e}")
        return ""

texts = []
metadatas = []

for root, _, files in os.walk(DATA_PATH):
    for file in files:
        path = os.path.join(root, file)
        lower = file.lower()
        if lower.endswith('.pdf'):
            text = load_pdf(path)
        elif lower.endswith('.docx') or lower.endswith('.doc'):
            text = load_docx(path)
        else:
            # skip unknown file types
            continue

        if not text:
            continue

        texts.append(text)
        metadatas.append({"source": path})

print(f"Loaded {len(texts)} documents from {DATA_PATH}")

if len(texts) == 0:
    print("No documents to process. Put PDFs/DOCX into the `data/` folder.")
    raise SystemExit(1)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    chunks = []
    start = 0
    text_length = len(text)
    while start < text_length:
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
        if start < 0:
            start = 0
    return chunks

all_texts = []
all_metadatas = []
for txt, md in zip(texts, metadatas):
    chunks = chunk_text(txt, chunk_size=500, overlap=50)
    for c in chunks:
        all_texts.append(c)
        all_metadatas.append(md)

print(f"Split into {len(all_texts)} chunks")

embeddings = OpenAIEmbeddings()
db = FAISS.from_texts(all_texts, embeddings, metadatas=all_metadatas)
db.save_local("vectorstore")

print("Ingestion complete. Vectorstore saved to ./vectorstore/")
