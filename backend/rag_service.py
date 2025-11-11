"""
RAG Service for University Chatbot
Handles vector search and context retrieval
"""

import os
from typing import List, Dict
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class RAGService:
    def __init__(self):
        # Initialize Qdrant client
        self.qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY")
        self.collection_name = os.getenv("COLLECTION_NAME", "university_knowledge")
        
        # Connect to Qdrant
        if self.qdrant_api_key:
            self.client = QdrantClient(url=self.qdrant_url, api_key=self.qdrant_api_key)
        else:
            self.client = QdrantClient(url=self.qdrant_url)
        
        # Initialize embedding model (same as ingestion)
        logger.info("Loading embedding model...")
        self.embedder = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info(f"RAG Service initialized with collection: {self.collection_name}")
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant documents
        
        Args:
            query: User question
            top_k: Number of results to return
            
        Returns:
            List of relevant documents with scores
        """
        try:
            # Generate query embedding
            query_vector = self.embedder.encode(query).tolist()
            
            # Search in Qdrant
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    'text': result.payload.get('text', ''),
                    'score': float(result.score),
                    'metadata': result.payload.get('metadata', {})
                })
            
            logger.info(f"Found {len(results)} relevant documents for query: {query[:50]}...")
            return results
        
        except Exception as e:
            logger.error(f"Error searching: {e}")
            return []
    
    def build_context(self, search_results: List[Dict]) -> str:
        """Build context string from search results"""
        if not search_results:
            return "No relevant information found in the knowledge base."
        
        context_parts = []
        for i, result in enumerate(search_results, 1):
            source = result['metadata'].get('source', 'Unknown')
            text = result['text']
            score = result['score']
            
            context_parts.append(
                f"[Source {i}: {source} (Relevance: {score:.3f})]\n{text}\n"
            )
        
        return "\n".join(context_parts)
    
    def build_prompt(self, query: str, context: str) -> str:
        """Build prompt for LLM with context"""
        prompt = f"""You are a helpful university chatbot assistant. Answer the student's question based on the provided context from the university knowledge base.

Context from Knowledge Base:
{context}

Student Question: {query}

Instructions:
- Answer the question based ONLY on the provided context
- If the context doesn't contain relevant information, say "I don't have information about that in my knowledge base"
- Be concise, friendly, and helpful
- Cite the source when providing specific information
- If multiple sources have different information, mention both

Answer:"""
        
        return prompt
    
    def get_relevant_context(self, query: str, top_k: int = 5) -> tuple[str, List[Dict]]:
        """
        Get relevant context for a query
        
        Returns:
            Tuple of (context_string, search_results)
        """
        # Search for relevant documents
        search_results = self.search(query, top_k)
        
        # Build context
        context = self.build_context(search_results)
        
        return context, search_results


# Global instance
rag_service = None

def get_rag_service() -> RAGService:
    """Get or create RAG service instance"""
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
    return rag_service