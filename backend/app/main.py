"""
FastAPI Main Application Entrypoint.
HH Goa 2026 — Voice-Enabled RAG System (Team TechTadkaa).
"""

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.schemas.rag_schemas import (
    HealthResponse,
    QueryRequest,
    QueryResponse,
    LatencyMetrics,
    GuardrailResult
)
from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for warm startup of models and database connections."""
    logger.info("Initializing application services...")
    start_time = time.perf_counter()

    # Preload Indic embedding model in memory
    embedding_service.load_model()

    # Initialize Qdrant client connection
    qdrant_service.initialize_client()

    startup_ms = (time.perf_counter() - start_time) * 1000
    logger.info(f"Application services initialized successfully in {startup_ms:.2f}ms")

    yield

    logger.info("Shutting down application services...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Voice-Enabled RAG System for MSMARCO-XI Indic & Multilingual Dataset",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Info"])
async def root_info():
    """Root info endpoint."""
    return {
        "team": "TechTadkaa",
        "system": settings.APP_NAME,
        "status": "operational",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint verifying embedding model & Qdrant vector DB status."""
    qdrant_ok = qdrant_service.client is not None
    embedding_ok = embedding_service.model is not None

    return HealthResponse(
        status="ok" if (qdrant_ok and embedding_ok) else "degraded",
        app_name=settings.APP_NAME,
        environment=settings.ENVIRONMENT,
        embedding_model=settings.EMBEDDING_MODEL_NAME,
        qdrant_connected=qdrant_ok,
    )


from backend.app.engine.rag_graph import run_rag_pipeline


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG Pipeline"])
async def rag_query(req: QueryRequest):
    """
    Full LangGraph Voice-RAG pipeline endpoint.
    Executes embed_query -> retrieve -> grade -> generate -> validate_grounding.
    Returns complete response with per-stage latency breakdown.
    """
    if not req.query_text.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Query text cannot be empty.")

    response = await run_rag_pipeline(
        query_text=req.query_text,
        language=req.language or "hi",
        top_k=req.top_k
    )
    return response
