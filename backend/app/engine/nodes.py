"""
LangGraph Node Implementations.
Each node takes and returns typed RAGGraphState with timing hooks.
"""

import time
import logging
from backend.app.engine.state import RAGGraphState
from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service
from backend.app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


async def node_embed_and_retrieve(state: RAGGraphState) -> RAGGraphState:
    """
    Node 1: Query Vectorization + Vector DB ANN Search (Retrieval Leg).
    Target Latency: 80-100ms
    """
    logger.info("Executing Graph Node: embed_and_retrieve")
    leg_start = time.perf_counter()

    query = state.get("query_text", "")
    top_k = state.get("top_k", 5)
    lang = state.get("language", "hi")

    # 1. Query Vectorization
    vec, embed_ms = embedding_service.embed_query(query)

    # 2. Qdrant HNSW Search
    chunks, qdrant_ms = qdrant_service.search(query_vector=vec, top_k=top_k, language_filter=lang)

    retrieval_leg_ms = (time.perf_counter() - leg_start) * 1000

    latency = state.get("latency", {})
    latency["query_embedding_ms"] = round(embed_ms, 2)
    latency["qdrant_search_ms"] = round(qdrant_ms, 2)
    latency["retrieval_leg_ms"] = round(retrieval_leg_ms, 2)

    return {
        **state,
        "query_vector": vec,
        "raw_chunks": chunks,
        "latency": latency
    }


async def node_grade_context(state: RAGGraphState) -> RAGGraphState:
    """
    Node 2: Grades context relevance.
    """
    logger.info("Executing Graph Node: grade_context")
    query = state.get("query_text", "")
    raw_chunks = state.get("raw_chunks", [])

    relevant_chunks, grade_ms = await llm_service.grade_context(query, raw_chunks)

    latency = state.get("latency", {})
    latency["grade_ms"] = round(grade_ms, 2)

    return {
        **state,
        "relevant_chunks": relevant_chunks,
        "latency": latency
    }


async def node_generate(state: RAGGraphState) -> RAGGraphState:
    """
    Node 3: Answers user query using Groq LLM inference.
    """
    logger.info("Executing Graph Node: generate")
    query = state.get("query_text", "")
    relevant_chunks = state.get("relevant_chunks", [])
    lang = state.get("language", "hi")

    answer, gen_ms = await llm_service.generate_response(query, relevant_chunks, language=lang)

    latency = state.get("latency", {})
    latency["generation_ms"] = round(gen_ms, 2)

    return {
        **state,
        "answer": answer,
        "latency": latency
    }


async def node_validate_grounding(state: RAGGraphState) -> RAGGraphState:
    """
    Node 4: Grounding and hallucination verification.
    """
    logger.info("Executing Graph Node: validate_grounding")
    query = state.get("query_text", "")
    answer = state.get("answer", "")
    relevant_chunks = state.get("relevant_chunks", [])

    is_grounded, guard_ms = await llm_service.validate_grounding(query, answer, relevant_chunks)

    latency = state.get("latency", {})
    latency["guardrail_ms"] = round(guard_ms, 2)

    guardrail = {
        "is_safe": True,
        "is_in_domain": True,
        "is_grounded": is_grounded,
        "confidence_score": 0.95 if is_grounded else 0.40,
        "reasoning": "PASSED" if is_grounded else "FAIL_UNGROUNDED"
    }

    return {
        **state,
        "is_grounded": is_grounded,
        "guardrail": guardrail,
        "latency": latency
    }
