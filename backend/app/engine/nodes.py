"""
LangGraph Node Implementations with Guardrails.
Each node takes and returns typed RAGGraphState with timing hooks and safety checks.
"""

import time
import logging
from backend.app.engine.state import RAGGraphState
from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service
from backend.app.services.llm_service import llm_service
from backend.app.engine.guardrails import (
    check_input_safety,
    check_off_topic_or_out_of_corpus,
    generate_refusal_answer
)

logger = logging.getLogger(__name__)


async def node_embed_and_retrieve(state: RAGGraphState) -> RAGGraphState:
    """
    Node 1: Query Vectorization + Vector DB ANN Search (Retrieval Leg) + Safety Pass.
    Target Latency: 80-100ms
    """
    logger.info("Executing Graph Node: embed_and_retrieve")
    leg_start = time.perf_counter()

    query = state.get("query_text", "")
    top_k = state.get("top_k", 5)
    lang = state.get("language", "hi")

    # 1. Moderation Safety Pass
    is_safe, safety_reason = check_input_safety(query)
    if not is_safe:
        logger.warning(f"Guardrail Flagged Unsafe Input: {safety_reason}")
        latency = state.get("latency", {})
        latency["retrieval_leg_ms"] = round((time.perf_counter() - leg_start) * 1000, 2)
        return {
            **state,
            "is_safe": False,
            "answer": generate_refusal_answer(safety_reason, language=lang),
            "latency": latency,
            "guardrail": {
                "is_safe": False,
                "is_in_domain": False,
                "is_grounded": True,
                "confidence_score": 0.0,
                "reasoning": safety_reason
            }
        }

    # 2. Query Vectorization
    vec, embed_ms = embedding_service.embed_query(query)

    # 3. Qdrant HNSW Search
    chunks, qdrant_ms = qdrant_service.search(query_vector=vec, top_k=top_k, language_filter=lang)

    retrieval_leg_ms = (time.perf_counter() - leg_start) * 1000

    latency = state.get("latency", {})
    latency["query_embedding_ms"] = round(embed_ms, 2)
    latency["qdrant_search_ms"] = round(qdrant_ms, 2)
    latency["retrieval_leg_ms"] = round(retrieval_leg_ms, 2)

    return {
        **state,
        "is_safe": True,
        "query_vector": vec,
        "raw_chunks": chunks,
        "latency": latency
    }


async def node_grade_context(state: RAGGraphState) -> RAGGraphState:
    """
    Node 2: Grades context relevance and off-topic out-of-corpus detection.
    """
    logger.info("Executing Graph Node: grade_context")
    if state.get("is_safe") is False:
        return state

    query = state.get("query_text", "")
    raw_chunks = state.get("raw_chunks", [])

    # Off-topic / Out-of-corpus check
    is_in_domain, domain_reason = check_off_topic_or_out_of_corpus(query, raw_chunks)

    relevant_chunks, grade_ms = await llm_service.grade_context(query, raw_chunks)

    latency = state.get("latency", {})
    latency["grade_ms"] = round(grade_ms, 2)

    return {
        **state,
        "is_in_domain": is_in_domain,
        "relevant_chunks": relevant_chunks if is_in_domain else [],
        "latency": latency
    }


async def node_generate(state: RAGGraphState) -> RAGGraphState:
    """
    Node 3: Answers user query or returns explicit refusal for out-of-corpus queries.
    """
    logger.info("Executing Graph Node: generate")
    if state.get("is_safe") is False:
        return state

    lang = state.get("language", "hi")
    query = state.get("query_text", "")
    is_in_domain = state.get("is_in_domain", True)
    relevant_chunks = state.get("relevant_chunks", [])

    if not is_in_domain or not relevant_chunks:
        answer = generate_refusal_answer("OUT_OF_CORPUS", language=lang)
        gen_ms = 0.0
    else:
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
    if state.get("is_safe") is False:
        return state

    query = state.get("query_text", "")
    answer = state.get("answer", "")
    relevant_chunks = state.get("relevant_chunks", [])
    is_in_domain = state.get("is_in_domain", True)

    if not is_in_domain or "अपर्याप्त जानकारी" in answer:
        is_grounded = True
        guard_ms = 0.0
    else:
        is_grounded, guard_ms = await llm_service.validate_grounding(query, answer, relevant_chunks)

    latency = state.get("latency", {})
    latency["guardrail_ms"] = round(guard_ms, 2)

    guardrail = {
        "is_safe": state.get("is_safe", True),
        "is_in_domain": is_in_domain,
        "is_grounded": is_grounded,
        "confidence_score": 0.95 if (is_in_domain and is_grounded) else 0.30,
        "reasoning": "PASSED" if (is_in_domain and is_grounded) else "REFUSAL_OUT_OF_CORPUS"
    }

    return {
        **state,
        "is_grounded": is_grounded,
        "guardrail": guardrail,
        "latency": latency
    }
