"""
Phase 3 Verification Script.
Tests:
1. LangGraph StateGraph pipeline execution (embed -> retrieve -> grade -> generate -> validate).
2. Groq LLM response generation and grounding validation.
3. Per-stage latency metrics tracking (ensuring retrieval_leg_ms < 100ms).
"""

import os
import sys
import asyncio
import logging

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service
from backend.app.engine.rag_graph import run_rag_pipeline
from ingestion.index_passages import index_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_phase3")


async def verify_phase3():
    logger.info("==========================================")
    logger.info("Starting Phase 3 Component Verification")
    logger.info("==========================================")

    # 1. Index test collection
    logger.info("Indexing test corpus into Qdrant vector DB...")
    index_res = index_dataset(strategy="metadata_aware")
    logger.info(f"✓ Indexed {index_res.get('total_chunks')} chunks successfully.")

    # 2. Test Hindi Query through LangGraph
    hindi_query = "गोवा की राजधानी क्या है?"
    logger.info(f"Running LangGraph RAG query: '{hindi_query}'...")

    response = await run_rag_pipeline(query_text=hindi_query, language="hi", top_k=3)

    logger.info("==========================================")
    logger.info(f"Query: {response.query}")
    logger.info(f"Generated Answer: {response.answer}")
    logger.info(f"Retrieved Chunks: {len(response.retrieved_chunks)}")
    if response.retrieved_chunks:
        logger.info(f"  Top Match: [{response.retrieved_chunks[0].doc_id}] {response.retrieved_chunks[0].text} (Score: {response.retrieved_chunks[0].score:.4f})")
    
    logger.info("--- PER-STAGE LATENCY BREAKDOWN ---")
    logger.info(f"  Query Embedding Latency: {response.latency.query_embedding_ms} ms")
    logger.info(f"  Qdrant HNSW Search Latency: {response.latency.qdrant_search_ms} ms")
    logger.info(f"  Combined Retrieval Leg Latency: {response.latency.retrieval_leg_ms} ms (Target: <100ms)")
    logger.info(f"  Guardrail Validation Latency: {response.latency.guardrail_ms} ms")
    logger.info(f"  LLM Generation Latency: {response.latency.generation_ms} ms")
    logger.info(f"  Total End-to-End Latency: {response.latency.total_e2e_ms} ms")

    logger.info("--- GUARDRAIL EVALUATION ---")
    logger.info(f"  Is Safe: {response.guardrail.is_safe}")
    logger.info(f"  Is Grounded: {response.guardrail.is_grounded}")
    logger.info(f"  Confidence Score: {response.guardrail.confidence_score}")
    logger.info(f"  Reasoning: {response.guardrail.reasoning}")
    logger.info("==========================================")

    # Verification checks
    assert response.latency.retrieval_leg_ms < 100.0, f"Retrieval leg exceeded 100ms: {response.latency.retrieval_leg_ms}ms"
    assert len(response.retrieved_chunks) > 0, "No chunks retrieved."
    assert response.guardrail.is_grounded is True, "Answer failed grounding validation."

    logger.info("✓ Phase 3 LangGraph Pipeline & Latency Verification Complete!")


if __name__ == "__main__":
    asyncio.run(verify_phase3())
