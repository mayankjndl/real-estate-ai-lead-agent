import json
import os
from functools import lru_cache

import faiss
import google.generativeai as genai
import numpy as np

from config import settings

genai.configure(api_key=settings.GEMINI_API_KEY)

def get_embeddings(texts: list[str]):
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=texts,
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

@lru_cache(maxsize=128)
def get_query_embedding_cached(text: str):
    """
    Cached version of get_query_embedding.
    Avoids a live Gemini Embedding API round-trip for repeated/similar queries.
    Cache holds up to 128 unique queries per process lifetime.
    """
    return get_query_embedding(text)

# Load FAQ data and initialize FAISS index (fail-safe for cloud deploys)
import logging as _rag_log
import threading
_logger = _rag_log.getLogger("rag")

RAG_AVAILABLE = False
data = []
index = None
_index_ready_event = threading.Event()

def _build_rag_index():
    global RAG_AVAILABLE, data, index
    try:
        faq_path = os.path.join(os.path.dirname(__file__), "data", "faq.json")
        with open(faq_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        texts = [
            f"{item['location']} {item['type']} property {item['details']} {item['description']}"
            for item in data
        ]

        # Compute embeddings in batch
        embeddings_list = get_embeddings(texts)
        embeddings = np.array(embeddings_list, dtype=np.float32)

        dimension = embeddings.shape[1]
        _idx = faiss.IndexFlatL2(dimension)
        _idx.add(embeddings)
        index = _idx
        RAG_AVAILABLE = True
        _index_ready_event.set()
        _logger.info(f"RAG index built with {len(data)} FAQ items.")
    except Exception as _e:
        _logger.warning(f"RAG index failed to build (degraded mode, no context injection): {_e}")

# Build in background so we don't block Uvicorn startup and hit Render's port timeout
threading.Thread(target=_build_rag_index, daemon=True).start()

def retrieve(query: str, k: int = 1):
    # Wait up to 5 seconds if index is still building (prevents empty results on early requests)
    if not RAG_AVAILABLE:
        _index_ready_event.wait(timeout=5.0)

    if not RAG_AVAILABLE or index is None:
        _logger.warning("RAG index is still building or failed, returning empty context.")
        return [], 0.0
    # Use cached embedding — avoids network call for repeated/similar queries
    q_emb = np.array([get_query_embedding_cached(query)], dtype=np.float32)
    D, I = index.search(q_emb, k)
    results = [data[i] for i in I[0]]
    score = float(D[0][0])
    return results, score
