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

# Load FAQ data and initialize FAISS index
faq_path = os.path.join(os.path.dirname(__file__), "data", "faq.json")
with open(faq_path, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [
    f"{item['location']} {item['type']} property {item['details']} {item['description']}"
    for item in data
]

# Compute embeddings
embeddings = np.array([get_embedding(t) for t in texts], dtype=np.float32)

# Initialize FAISS
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

def retrieve(query: str, k: int = 2):
    q_emb = np.array([get_query_embedding(query)], dtype=np.float32)
    D, I = index.search(q_emb, k)
    
    results = [data[i] for i in I[0]]
    # Lower distance means higher similarity.
    # Adjust this threshold as needed based on the embedding space.
    # L2 distance for embedding-001 can vary, let's return the score anyway.
    score = float(D[0][0])
    
    return results, score
