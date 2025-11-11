from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai
from dotenv import load_dotenv
import os
import asyncio
import time
import logging
from typing import Optional, List
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="University Assistant API",
    version="2.1",
    description="RAG-based chatbot for university queries"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Add your deployed frontend URL below when available
        # "https://your-app.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gemini AI Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables")

genai.configure(api_key=GEMINI_API_KEY)
MODEL = genai.GenerativeModel("models/gemini-2.0-flash-exp")

# Qdrant Configuration
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "university_knowledge")

if not QDRANT_URL or not QDRANT_API_KEY:
    raise ValueError("QDRANT credentials not found in environment variables")

# Initialize Qdrant client and embedder
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
embedder = SentenceTransformer("all-mpnet-base-v2")

# Request/Response Models
class Question(BaseModel):
    question: str
    top_k: Optional[int] = 5

class Source(BaseModel):
    source: str
    score: float

class ChatResponse(BaseModel):
    answer: str
    sources: List[Source]
    response_time: Optional[float] = None

# Enhanced prompt template
SYSTEM_PROMPT = """You are a helpful and professional university assistant for VIT-AP University.

**Instructions:**
- Use ONLY the context provided below to answer questions
- Format your responses using proper Markdown:
  - Use **bold** for headings and important information
  - Use bullet points (-) for lists
  - Use numbered lists (1., 2., 3.) for sequential information
  - Use tables when comparing multiple items
- Always structure fee information in a clear, organized format
- If information is not in the context, politely say "I don't have that information in my knowledge base. Please visit vitap.ac.in for more details."
- Be concise but comprehensive
- Always end with a note directing users to the official website for the most current information

**Context:**
{context}

**Question:**
{question}

**Answer:**"""

@app.post("/ask", response_model=ChatResponse)
async def ask_question(q: Question):
    """
    Process user questions using RAG pipeline with Qdrant and Gemini
    """
    start_time = time.time()
    
    try:
        if not q.question or len(q.question.strip()) == 0:
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if len(q.question) > 500:
            raise HTTPException(status_code=400, detail="Question too long (max 500 characters)")
        
        logger.info(f"Processing question: {q.question[:50]}...")
        
        # Generate embedding
        query_vector = embedder.encode(q.question).tolist()
        
        # Search Qdrant
        search_results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            limit=q.top_k
        )
        
        if not search_results:
            logger.warning("No relevant documents found in Qdrant")
            return ChatResponse(
                answer="I couldn't find relevant information in my knowledge base. Please visit [vitap.ac.in](https://vitap.ac.in/) for more details.",
                sources=[],
                response_time=round(time.time() - start_time, 2)
            )
        
        # Build context
        context = "\n\n---\n\n".join([
            f"Source: {r.payload['metadata']['source']}\n{r.payload['text']}"
            for r in search_results
        ])
        
        # Create enhanced prompt
        prompt = SYSTEM_PROMPT.format(
            context=context,
            question=q.question
        )
        
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: MODEL.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "top_p": 0.8,
                    "top_k": 40,
                    "max_output_tokens": 1024,
                }
            )
        )
        
        answer = response.text.strip()
        
        if "vitap.ac.in" not in answer.lower():
            answer += "\n\n*For the most current information, please visit [vitap.ac.in](https://vitap.ac.in/)*"
        
        sources = [
            Source(
                source=r.payload["metadata"]["source"],
                score=round(r.score, 3)
            )
            for r in search_results
        ]
        
        response_time = round(time.time() - start_time, 2)
        logger.info(f"Response generated in {response_time}s")
        
        return ChatResponse(
            answer=answer,
            sources=sources,
            response_time=response_time
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred while processing your question. Please try again."
        )

@app.get("/health")
def health_check():
    """
    Health check endpoint to verify all services are running
    """
    try:
        MODEL.generate_content("ping", generation_config={"max_output_tokens": 5})
        client.get_collection(COLLECTION_NAME)
        
        return {
            "status": "healthy",
            "gemini": "connected",
            "qdrant": "connected",
            "version": "2.1"
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.get("/")
def root():
    """
    Root endpoint with API information
    """
    return {
        "message": "University RAG Chatbot API",
        "version": "2.1",
        "endpoints": {
            "ask": "/ask",
            "health": "/health",
            "docs": "/docs"
        }
    }

# ✅ This is the correct way for Railway to detect and run your app
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))  # Railway assigns PORT dynamically
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
