"""
Typed Graph State Definition for LangGraph Pipeline.
"""

from typing import TypedDict, Optional, Any
from backend.app.schemas.rag_schemas import PassageChunk, LatencyMetrics, GuardrailResult


class RAGGraphState(TypedDict, total=False):
    """Structured graph state passed across all LangGraph nodes."""
    query_text: str
    language: str
    top_k: int
    query_vector: list[float]
    raw_chunks: list[PassageChunk]
    relevant_chunks: list[PassageChunk]
    answer: str
    is_grounded: bool
    is_safe: bool
    retry_count: int
    error_message: Optional[str]
    latency: dict[str, float]
    guardrail: dict[str, Any]
