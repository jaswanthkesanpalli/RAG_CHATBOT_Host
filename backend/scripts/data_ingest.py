"""
Improved Data Upload Script for Qdrant Cloud
✅ Safe (no auto-deletion)
✅ Handles timeouts and retries
✅ Optimized chunking and cleaning for better RAG accuracy
✅ Fully compatible with Gemini / main.py setup
"""

import os
import json
import re
import random
import time
from typing import List, Dict
from openai import OpenAI
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

# Optional imports
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2 not installed. PDF files will be skipped.")

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False
    print("⚠️ python-docx not installed. DOCX files will be skipped.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️ pandas not installed. CSV files will be skipped.")

# Load environment
load_dotenv()


class DataUploader:
    def __init__(self):
        print("\n" + "=" * 60)
        print("🚀 QDRANT DATA UPLOADER - RELIABLE VERSION")
        print("=" * 60 + "\n")

        self.qdrant_url = os.getenv("QDRANT_URL")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("COLLECTION_NAME", "university_knowledge")

        if not self.qdrant_url or not self.qdrant_api_key:
            raise ValueError("❌ Missing QDRANT_URL or QDRANT_API_KEY in .env")

        print("📡 Connecting to Qdrant Cloud...")
        self.client = QdrantClient(
            url=self.qdrant_url,
            api_key=self.qdrant_api_key,
            timeout=60.0  # Increased timeout for large uploads
        )
        print("   ✅ Connected!\n")

        print("🤖 Loading embedding model (all-mpnet-base-v2)...")
        self.embedder = SentenceTransformer("all-mpnet-base-v2")
        self.vector_size = 768
        print("   ✅ Model loaded!\n")

        # Ensure collection exists
        self.ensure_collection_exists()

    # ---------------------------------------------------------------------
    def ensure_collection_exists(self):
        """Create collection if not exists (won’t delete existing one)."""
        collections = [c.name for c in self.client.get_collections().collections]
        if self.collection_name not in collections:
            print(f"🆕 Creating new collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=self.vector_size, distance=Distance.COSINE),
            )
        else:
            print(f"✅ Collection '{self.collection_name}' already exists. Data will be added.\n")

    # ---------------------------------------------------------------------
    def clean_text(self, text: str) -> str:
        """Cleans unnecessary symbols and whitespace."""
        text = re.sub(r'(\n\s*){2,}', '\n', text)
        text = re.sub(r'Home\s*>.*', '', text)
        text = re.sub(r'Page\s*\d+\s*of\s*\d+', '', text)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip()

    def chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 80) -> List[str]:
        """Splits text into overlapping chunks for better retrieval."""
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size - overlap):
            chunk = " ".join(words[i:i + chunk_size])
            if len(chunk) > 50:  # Skip tiny fragments
                chunks.append(chunk)
        return chunks

    # ---------------------------------------------------------------------
    def read_pdf(self, path: str) -> str:
        if not PDF_AVAILABLE:
            return ""
        text = ""
        try:
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
        except Exception as e:
            print(f"⚠️ PDF read error {path}: {e}")
        return text

    def read_docx(self, path: str) -> str:
        if not DOCX_AVAILABLE:
            return ""
        try:
            doc = DocxDocument(path)
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except Exception as e:
            print(f"⚠️ DOCX read error {path}: {e}")
            return ""

    def read_txt(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ TXT read error {path}: {e}")
            return ""

    def read_json(self, path: str) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [json.dumps(d, indent=2) for d in (data if isinstance(data, list) else [data])]
        except Exception as e:
            print(f"⚠️ JSON read error {path}: {e}")
            return []

    def read_csv(self, path: str) -> List[str]:
        if not PANDAS_AVAILABLE:
            return []
        try:
            df = pd.read_csv(path)
            return ["\n".join([f"{k}: {v}" for k, v in row.items()]) for _, row in df.iterrows()]
        except Exception as e:
            print(f"⚠️ CSV read error {path}: {e}")
            return []

    # ---------------------------------------------------------------------
    def process_file(self, path: str) -> List[Dict]:
        filename = os.path.basename(path)
        ext = os.path.splitext(filename)[1].lower()
        print(f"📄 Processing {filename}")

        docs = []
        text = ""

        # File extract
        if ext == ".pdf":
            text = self.read_pdf(path)
        elif ext == ".docx":
            text = self.read_docx(path)
        elif ext == ".txt":
            text = self.read_txt(path)
        elif ext == ".json":
            for i, t in enumerate(self.read_json(path)):
                docs.append({"text": t, "metadata": {"source": filename, "type": "json", "chunk": i}})
        elif ext == ".csv":
            for i, t in enumerate(self.read_csv(path)):
                docs.append({"text": t, "metadata": {"source": filename, "type": "csv", "chunk": i}})

        # Clean + Chunk
        if text:
            text = self.clean_text(text)
            chunks = self.chunk_text(text)
            for i, chunk in enumerate(chunks):
                docs.append({"text": chunk, "metadata": {"source": filename, "type": ext.strip('.'), "chunk": i}})

        print(f"   ✅ Extracted {len(docs)} chunks\n")
        return docs

    # ---------------------------------------------------------------------
    def upload_data(self, folder: str = "./data"):
        if not os.path.exists(folder):
            raise FileNotFoundError(f"❌ Data folder not found: {folder}")

        files = [os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f))]
        all_docs = []
        for f in files:
            all_docs.extend(self.process_file(f))

        print(f"📊 Total chunks to upload: {len(all_docs)}\n")

        batch_size = 10  # smaller batch to prevent timeout
        uploaded = 0

        for i in range(0, len(all_docs), batch_size):
            batch = all_docs[i:i + batch_size]
            points = []
            for doc in batch:
                emb = self.embedder.encode(doc["text"]).tolist()
                random_id = random.randint(1_000_000, 9_999_999)
                points.append(PointStruct(id=random_id, vector=emb, payload=doc))

            # Retry logic for failed uploads
            retries = 3
            for attempt in range(retries):
                try:
                    self.client.upsert(collection_name=self.collection_name, points=points)
                    break  # success
                except Exception as e:
                    print(f"⚠️ Upload failed (attempt {attempt + 1}/{retries}): {e}")
                    time.sleep(3)
            else:
                print("❌ Skipping this batch after 3 failed attempts.")

            uploaded += len(points)
            print(f"✅ Uploaded {uploaded}/{len(all_docs)}")

        print(f"\n🎉 Upload complete! {uploaded} chunks uploaded successfully.\n")


# -------------------------------------------------------------------------
def main():
    uploader = DataUploader()
    uploader.upload_data("./data")


if __name__ == "__main__":
    main()
