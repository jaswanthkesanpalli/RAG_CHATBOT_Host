"""
Test Retrieval Script for Qdrant (to verify RAG data quality)
"""

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

load_dotenv()

# ---------------- CONFIG ----------------
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "university_knowledge")
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Same embedding model used in data_ingest.py
EMBEDDER = SentenceTransformer("all-mpnet-base-v2")

# ---------------- CONNECT ----------------
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
print(f"✅ Connected to Qdrant collection: {COLLECTION_NAME}\n")

# ---------------- TEST FUNCTION ----------------
def test_query(query_text: str, top_k: int = 3):
    query_vector = EMBEDDER.encode(query_text).tolist()
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=top_k
    )
    print(f"🔍 Query: {query_text}")
    print("-" * 80)
    for i, r in enumerate(results, 1):
        print(f"[{i}] Score: {r.score:.4f}")
        print(f"Source: {r.payload['metadata']['source']}")
        print(f"Text:\n{r.payload['text'][:400]}...")
        print("-" * 80)
    print("\n")

# ---------------- SAMPLE QUERIES ----------------
test_query("When does B.Tech admission start?")
test_query("Who is the head of the computer science department?")
test_query("What is the average package offered in placements?")
test_query("List some facilities available on campus.")
