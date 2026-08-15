"""
Guardrail Engine for RAG Pipeline.
Implements:
1. Off-topic domain detector (verifies query relevance against MSMARCO / Indic context).
2. Unsafe/inappropriate input moderation filter.
3. Explicit "knows when not to answer" refusal generator for out-of-corpus queries.
"""

import time
import logging
from backend.app.schemas.rag_schemas import PassageChunk, GuardrailResult

logger = logging.getLogger(__name__)

# Basic safety blocklist patterns for input moderation
UNSAFE_KEYWORDS = [
    "bomb", "explosive", "hack", "malware", "virus", "attack",
    "illegal", "weapon", "kill", "harm"
]


def check_input_safety(query: str) -> tuple[bool, str]:
    """
    Moderation pass checking for unsafe input content.
    Returns (is_safe, reason).
    """
    query_lower = query.lower()
    for kw in UNSAFE_KEYWORDS:
        if kw in query_lower:
            return False, f"UNSAFE_INPUT_DETECTED: '{kw}'"
    return True, "SAFE"


def check_off_topic_or_out_of_corpus(
    query: str,
    retrieved_chunks: list[PassageChunk],
    min_score_threshold: float = 0.78
) -> tuple[bool, str]:
    """
    Fast check verifying if query is in-domain for MSMARCO / Indic corpus.
    If top retrieved chunk similarity score < min_score_threshold, marks query as out-of-corpus.
    Returns (is_in_domain, reasoning).
    """
    if not retrieved_chunks:
        return False, "OUT_OF_CORPUS_NO_PASSAGES"

    top_chunk = retrieved_chunks[0]
    if top_chunk.score < min_score_threshold:
        return False, f"LOW_CONFIDENCE_SCORE: {top_chunk.score:.4f} < {min_score_threshold}"

    return True, "IN_DOMAIN"


def generate_refusal_answer(reason: str, language: str = "hi") -> str:
    """Generates explicit refusal response when guardrails block a query."""
    if "UNSAFE" in reason:
        return "सुरक्षा नीति उल्लंघन: इस प्रश्न का उत्तर नहीं दिया जा सकता।"
    
    return "अपर्याप्त जानकारी: यह प्रश्न उपलब्ध ज्ञान संदर्भ के बाहर है।"
