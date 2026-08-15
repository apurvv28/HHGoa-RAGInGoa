"""
LangGraph Workflow Builder & Compiler.
Assembles state graph: retrieve -> grade -> generate -> validate -> END.
"""

import time
import logging
from typing import Any
from langgraph.graph import StateGraph, START, END # type: ignore

from backend.app.engine.state import RAGGraphState
from backend.app.engine.nodes import (
    node_embed_and_retrieve,
    node_grade_context,
    node_generate,
    node_validate_grounding
)
from backend.app.schemas.rag_schemas import QueryResponse, LatencyMetrics, GuardrailResult, PassageChunk

logger = logging.getLogger(__name__)


def build_rag_graph():
    """Builds and compiles the LangGraph RAG pipeline."""
    workflow = StateGraph(RAGGraphState)

    # 1. Add nodes
    workflow.add_node("retrieve", node_embed_and_retrieve)
    workflow.add_node("grade", node_grade_context)
    workflow.add_node("generate", node_generate)
    workflow.add_node("validate", node_validate_grounding)

    # 2. Add edges
    workflow.add_edge(START, "retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_edge("grade", "generate")
    workflow.add_edge("generate", "validate")
    workflow.add_edge("validate", END)

    # 3. Compile graph
    app = workflow.compile()
    logger.info("LangGraph RAG pipeline built and compiled successfully.")
    return app


# Compiled pipeline instance
rag_app = build_rag_graph()


async def run_rag_pipeline(query_text: str, language: str = "hi", top_k: int = 5) -> QueryResponse:
    """
    Executes full RAG graph pipeline and returns formatted QueryResponse with latency breakdown.
    """
    pipeline_start = time.perf_counter()

    initial_state: RAGGraphState = {
        "query_text": query_text,
        "language": language,
        "top_k": top_k,
        "retry_count": 0,
        "latency": {"stt_ms": 0.0, "tts_ms": 0.0}
    }

    try:
        final_state = await rag_app.ainvoke(initial_state)
    except Exception as e:
        logger.error(f"Error during LangGraph pipeline execution: {e}")
        final_state = initial_state
        final_state["answer"] = "सिस्टम में तकनीकी खराबी आ गई है। कृपया पुनः प्रयास करें।"
        final_state["relevant_chunks"] = []

    total_e2e_ms = (time.perf_counter() - pipeline_start) * 1000

    lat_dict = final_state.get("latency", {})
    lat_dict["total_e2e_ms"] = round(total_e2e_ms, 2)

    metrics = LatencyMetrics(
        stt_ms=lat_dict.get("stt_ms", 0.0),
        query_embedding_ms=lat_dict.get("query_embedding_ms", 0.0),
        qdrant_search_ms=lat_dict.get("qdrant_search_ms", 0.0),
        retrieval_leg_ms=lat_dict.get("retrieval_leg_ms", 0.0),
        guardrail_ms=lat_dict.get("guardrail_ms", 0.0),
        generation_ms=lat_dict.get("generation_ms", 0.0),
        tts_ms=lat_dict.get("tts_ms", 0.0),
        total_e2e_ms=round(total_e2e_ms, 2),
    )

    guard_dict = final_state.get("guardrail", {})
    guardrail = GuardrailResult(
        is_safe=guard_dict.get("is_safe", True),
        is_in_domain=guard_dict.get("is_in_domain", True),
        is_grounded=guard_dict.get("is_grounded", True),
        confidence_score=guard_dict.get("confidence_score", 1.0),
        reasoning=guard_dict.get("reasoning", "PASSED"),
    )

    chunks: list[PassageChunk] = final_state.get("relevant_chunks") or final_state.get("raw_chunks") or []

    return QueryResponse(
        query=query_text,
        answer=final_state.get("answer", "No answer generated."),
        retrieved_chunks=chunks,
        latency=metrics,
        guardrail=guardrail,
    )
