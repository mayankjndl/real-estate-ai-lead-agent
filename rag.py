import json
import faiss
import numpy as np
import google.generativeai as genai
import os
from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_embedding(text: str):
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document"
    )
    return result['embedding']

def get_query_embedding(text: str):
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query"
    )
    return result['embedding']

# Load FAQ data and initialize FAISS index (fail-safe for cloud deploys)
import logging as _rag_log
_logger = _rag_log.getLogger("rag")

RAG_AVAILABLE = False
data = []
index = None

try:
    faq_path = os.path.join(os.path.dirname(__file__), "data", "faq.json")
    with open(faq_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts = [
        f"{item['location']} {item['type']} property {item['details']} {item['description']}"
        for item in data
    ]

    # Compute embeddings (may fail on free tier rate limits)
    embeddings = np.array([get_embedding(t) for t in texts], dtype=np.float32)

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)
    RAG_AVAILABLE = True
    _logger.info(f"RAG index built with {len(data)} FAQ items.")
except Exception as _e:
    _logger.warning(f"RAG index failed to build (degraded mode, no context injection): {_e}")

def retrieve(query: str, k: int = 2):
    if not RAG_AVAILABLE or index is None:
        raise RuntimeError("RAG index not available")
    q_emb = np.array([get_query_embedding(query)], dtype=np.float32)
    D, I = index.search(q_emb, k)
    results = [data[i] for i in I[0]]
    score = float(D[0][0])
    return results, score
