from typing import Any, Optional
from pydantic import BaseModel, Field


class PassageChunk(BaseModel):
    """Rich passage chunk with metadata for retrieval and attribution."""
    chunk_id: str = Field(..., description="Unique identifier for chunk")
    doc_id: str = Field(..., description="Source document/query ID from MSMARCO")
    text: str = Field(..., description="Passage text content")
    language: str = Field(default="en", description="Language code (e.g. 'hi', 'en')")
    score: float = Field(default=0.0, description="Similarity retrieval score")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata payload")


class QueryRequest(BaseModel):
    """Structured search query request."""
    query_text: str = Field(..., description="Input user query text")
    language: Optional[str] = Field(default=None, description="Language split override (e.g. 'hi', 'en')")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of passages to retrieve")
    strategy: str = Field(default="metadata_aware", description="Chunking/retrieval strategy")


class LatencyMetrics(BaseModel):
    """Detailed timing breakdown for each pipeline leg in milliseconds."""
    stt_ms: float = Field(default=0.0, description="Speech-to-Text conversion latency (ms)")
    query_embedding_ms: float = Field(default=0.0, description="Query vectorization latency (ms)")
    qdrant_search_ms: float = Field(default=0.0, description="Vector DB HNSW search latency (ms)")
    retrieval_leg_ms: float = Field(default=0.0, description="Combined retrieval leg latency (embed + search + context) (ms)")
    guardrail_ms: float = Field(default=0.0, description="Guardrails verification latency (ms)")
    generation_ms: float = Field(default=0.0, description="LLM generation latency (ms)")
    tts_ms: float = Field(default=0.0, description="Text-to-Speech synthesis latency (ms)")
    total_e2e_ms: float = Field(default=0.0, description="Total end-to-end pipeline latency (ms)")


class GuardrailResult(BaseModel):
    """Safety, topic relevancy, and hallucination grounding check results."""
    is_safe: bool = Field(default=True, description="Query safety moderation result")
    is_in_domain: bool = Field(default=True, description="Topic domain check result")
    is_grounded: bool = Field(default=True, description="Grounding verification result against context")
    confidence_score: float = Field(default=1.0, description="Guardrail confidence score")
    reasoning: str = Field(default="PASSED", description="Detailed status message or rejection reason")


class QueryResponse(BaseModel):
    """Structured response from the RAG graph pipeline."""
    query: str = Field(..., description="Original or transcribed user query")
    answer: str = Field(..., description="Generated answer or refusal message")
    retrieved_chunks: list[PassageChunk] = Field(default_factory=list, description="Retrieved context chunks")
    latency: LatencyMetrics = Field(default_factory=LatencyMetrics, description="Per-stage latency breakdown")
    guardrail: GuardrailResult = Field(default_factory=GuardrailResult, description="Guardrail evaluation results")


class HealthResponse(BaseModel):
    """System status check response."""
    status: str = Field(default="ok")
    app_name: str
    environment: str
    embedding_model: str
    qdrant_connected: bool
