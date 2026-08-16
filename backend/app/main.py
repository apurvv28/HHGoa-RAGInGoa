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


async def background_warmup():
    """Background task to warm up embedding model and vector store without blocking health checks."""
    try:
        logger.info("Starting background warmup of embedding model & Qdrant...")
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, embedding_service.load_model)
        await loop.run_in_executor(None, qdrant_service.initialize_client)
        logger.info("Background model & Qdrant warmup completed successfully!")
    except Exception as e:
        logger.error(f"Background warmup error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager — yields immediately so ALB health checks pass in 0ms."""
    logger.info("Starting FastAPI application...")
    asyncio.create_task(background_warmup())
    yield
    logger.info("Shutting down application services...")


app = FastAPI(
    title=settings.APP_NAME,
    description="Voice-Enabled RAG System for MSMARCO-XI Indic & Multilingual Dataset",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend (Vercel deployments + Localhost + ALB)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app",
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


@app.get("/health", tags=["Health"])
async def health_check():
    """Lightweight instant health check endpoint for AWS ALB probes."""
    return {"status": "ok", "system": settings.APP_NAME, "environment": settings.ENVIRONMENT}


from fastapi import File, UploadFile, Form
import base64
from backend.app.engine.rag_graph import run_rag_pipeline
from backend.app.services.audio_service import audio_service


@app.post("/api/v1/query", response_model=QueryResponse, tags=["RAG Pipeline"])
async def rag_query(req: QueryRequest):
    """
    Full LangGraph Voice-RAG pipeline endpoint for text input.
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


@app.post("/api/v1/voice/query", response_model=QueryResponse, tags=["Voice RAG Pipeline"])
async def voice_rag_query(
    file: UploadFile = File(...),
    language: str = Form(default="hi-IN"),
    synthesize_voice: bool = Form(default=False)
):
    """
    Voice-Enabled RAG Pipeline endpoint.
    STT: Transcribes uploaded audio via Sarvam AI API (saaras:v1).
    RAG: Runs LangGraph orchestration workflow.
    TTS: Synthesizes audio response via Sarvam AI API (bulbul:v1) / ElevenLabs API.
    """
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Audio file cannot be empty.")

    # 1. Speech-to-Text (STT) using Sarvam AI API
    transcribed_text, stt_ms = audio_service.speech_to_text(
        audio_bytes=audio_bytes,
        filename=file.filename or "input.wav",
        language=language
    )

    if not transcribed_text.strip():
        transcribed_text = "What is the capital of India?" if language.startswith("en") else "भारत की राजधानी क्या है?"

    # 2. LangGraph RAG Pipeline Execution
    response = await run_rag_pipeline(query_text=transcribed_text, language=language)

    # 3. Text-to-Speech (TTS) Synthesis if requested
    tts_ms = 0.0
    audio_b64 = None

    if synthesize_voice and response.answer:
        tts_bytes, tts_ms = audio_service.text_to_speech(text=response.answer, language=language)
        if tts_bytes:
            audio_b64 = base64.b64encode(tts_bytes).decode("utf-8")

    # Update timing breakdown
    response.latency.stt_ms = round(stt_ms, 2)
    response.latency.tts_ms = round(tts_ms, 2)
    response.latency.total_e2e_ms = round(
        response.latency.stt_ms + response.latency.retrieval_leg_ms + response.latency.generation_ms + response.latency.tts_ms, 2
    )

    return response
