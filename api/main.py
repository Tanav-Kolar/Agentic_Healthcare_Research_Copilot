"""Main FastAPI application entry point."""

import logging
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.schemas import AskRequest, AskResponse
from agents.orchestrator import ResearchPipeline
from config import settings

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Agentic Healthcare Research Copilot",
    description="Multi-agent medical research assistant powered by Gemma 3 and PubMed.",
    version="1.0.0",
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline as a singleton
pipeline = ResearchPipeline()

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": settings.ollama_model}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Execute the research pipeline for a clinical question.
    
    This invokes the 6-agent sequential pipeline:
    1. Query Understanding (PICO)
    2. Search / Retrieval (Direct RAG)
    3. Evidence Grading
    4. Contradiction Detection
    5. Synthesis
    6. Citation Verification
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    logger.info("Processing question for thread %s: %s", thread_id, request.question)
    
    try:
        # We run the pipeline synchronously for now since it involves heavy local LLM compute.
        # In a real production app, we would use BackgroundTasks or a job queue (Celery/Redis).
        response_data = pipeline.run(
            question=request.question,
            thread_id=thread_id,
            filters=request.filters.model_dump() if request.filters else None
        )
        return response_data
    except Exception as e:
        logger.error("Pipeline failure: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {str(e)}")

@app.get("/traces/{thread_id}")
async def get_traces(thread_id: str):
    """Retrieve agent message traces for a specific session."""
    # The 'pipeline' currently keeps traces in memory for the last run.
    # To support history, we would load from data/sample_traces/*.jsonl
    return {"thread_id": thread_id, "traces": pipeline.get_traces()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
