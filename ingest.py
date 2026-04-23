import os
from collections import defaultdict

import fitz  # PyMuPDF
import docx2txt
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS

from embedding_config import build_embeddings, write_embedding_meta

load_dotenv()

DATA_PATH = "data"
VECTORSTORE_DIR = "vectorstore"


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


def collect_document_paths(data_path: str) -> list[str]:
    """
    Walk data/ and pick one file per logical document. If the same title exists
    under sibling PDF/ and Word/ folders, keep the PDF only.
    """
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for root, _, files in os.walk(data_path):
        for file in files:
            path = os.path.join(root, file)
            lower = file.lower()
            if not (
                lower.endswith(".pdf")
                or lower.endswith(".docx")
                or lower.endswith(".doc")
            ):
                continue
            stem = os.path.splitext(file)[0]
            parent = os.path.basename(root)
            if parent.lower() in ("pdf", "word"):
                gp = os.path.dirname(root)
                key = (os.path.normpath(gp).lower(), stem.lower())
            else:
                key = (os.path.normpath(root).lower(), stem.lower())
            groups[key].append(path)
    selected: list[str] = []
    for paths in groups.values():
        pdfs = [p for p in paths if p.lower().endswith(".pdf")]
        if pdfs:
            selected.append(sorted(pdfs)[0])
            continue
        docxs = [p for p in paths if p.lower().endswith((".docx", ".doc"))]
        if docxs:
            selected.append(sorted(docxs)[0])
    return sorted(selected)


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


paths = collect_document_paths(DATA_PATH)
print(f"Selected {len(paths)} document file(s) after de-duplicating PDF/Word pairs")

texts: list[str] = []
metadatas: list[dict] = []
for path in paths:
    lower = path.lower()
    if lower.endswith(".pdf"):
        text = load_pdf(path)
    else:
        text = load_docx(path)
    if not text:
        continue
    texts.append(text)
    metadatas.append({"source": path})

print(f"Loaded {len(texts)} documents from {DATA_PATH}")

if len(texts) == 0:
    print("No documents to process. Put PDFs/DOCX into the `data/` folder.")
    raise SystemExit(1)

all_texts: list[str] = []
all_metadatas: list[dict] = []
for txt, md in zip(texts, metadatas):
    chunks = chunk_text(txt, chunk_size=500, overlap=50)
    for c in chunks:
        all_texts.append(c)
        all_metadatas.append(md)

print(f"Split into {len(all_texts)} chunks")

embeddings, emb_meta = build_embeddings()
db = FAISS.from_texts(all_texts, embeddings, metadatas=all_metadatas)
db.save_local(VECTORSTORE_DIR)
write_embedding_meta(VECTORSTORE_DIR, emb_meta)

print(f"Ingestion complete. Vectorstore saved to ./{VECTORSTORE_DIR}/")
print(
    f"Embeddings: {emb_meta.get('provider')} (set EMBEDDINGS_PROVIDER=openai to use OpenAI for indexing.)"
)
