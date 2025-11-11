"""
Qdrant Cloud Connection & Health Check Script
---------------------------------------------
This script checks:
✅ Successful connection to Qdrant Cloud
✅ Collection existence & total vectors (chunks)
✅ Optional sample search test

⚠️ It will NOT delete or modify your data.
"""

import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "university_knowledge")

print("\n" + "="*60)
print("🔍 QDRANT CLOUD HEALTH CHECK")
print("="*60)

# 1. Connect to Qdrant
try:
    print(f"📡 Connecting to Qdrant Cloud: {QDRANT_URL}")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    print("✅ Connection successful!\n")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# 2. Check if collection exists
try:
    collections = client.get_collections()
    collection_names = [col.name for col in collections.collections]

    if COLLECTION_NAME not in collection_names:
        print(f"⚠️ Collection '{COLLECTION_NAME}' not found.")
        print("💡 Run data_ingest.py first to create and upload data.")
        exit(0)
    else:
        print(f"✅ Collection '{COLLECTION_NAME}' found!\n")
except Exception as e:
    print(f"❌ Error fetching collections: {e}")
    exit(1)

# 3. Get collection details
try:
    collection_info = client.get_collection(COLLECTION_NAME)
    print("📊 COLLECTION INFO")
    print("-" * 60)
    print(f"Name: {COLLECTION_NAME}")
    print(f"Vector size: {collection_info.config.params.vectors.size}")
    print(f"Distance metric: {collection_info.config.params.vectors.distance}")
    print(f"Total vectors (chunks): {collection_info.vectors_count}")
    print(f"Status: ✅ Active")
    print("-" * 60 + "\n")
except Exception as e:
    print(f"❌ Error fetching collection info: {e}")
    exit(1)

# 4. Perform a small test search (optional)
try:
    print("🤖 Loading embedding model for test search...")
    embedder = SentenceTransformer('all-MiniLM-L6-v2')
    query = "Btech admission requirements"
    query_vector = embedder.encode(query).tolist()

    print(f"🔎 Performing search for: '{query}'")
    results = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vector,
        limit=3
    )

    if results:
        print(f"✅ Search returned {len(results)} results:\n")
        for i, res in enumerate(results, 1):
            meta = res.payload.get("metadata", {})
            src = meta.get("source", "Unknown")
            print(f"{i}. Score: {res.score:.3f} | Source: {src}")
            print(f"   Text: {res.payload['text'][:100]}...\n")
    else:
        print("⚠️ No results found (collection may be empty).")

except Exception as e:
    print(f"❌ Test search failed: {e}")

print("="*60)
print("🏁 QDRANT HEALTH CHECK COMPLETE")
print("="*60)
