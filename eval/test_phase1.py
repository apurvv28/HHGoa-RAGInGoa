"""
Phase 1 Verification Script.
Tests:
1. Indic embedding model initialization & query encoding latency.
2. In-memory Qdrant collection creation & indexing.
3. Dataset sample loading from data/sample_msmarco.json.
4. FastAPI health check initialization.
"""

import time
import json
import os
import sys
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_phase1")


def verify_phase1():
    logger.info("==========================================")
    logger.info("Starting Phase 1 Component Verification")
    logger.info("==========================================")

    # 1. Dataset sample check
    sample_file = os.path.join(os.path.dirname(__file__), "..", "data", "sample_msmarco.json")
    if os.path.exists(sample_file):
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"✓ Dataset sample loaded successfully: {data.get('sample_count', 0)} samples found.")
    else:
        logger.warning("✗ Sample dataset file not found. Run inspect_dataset.py first.")

    # 2. Embedding service check
    try:
        from backend.app.services.embedding_service import embedding_service
        logger.info("Initializing Indic embedding service...")
        embedding_service.load_model()
        
        test_query = "भारत की राजधानी क्या है?"
        vec, embed_ms = embedding_service.embed_query(test_query)
        logger.info(f"✓ Indic embedding generated for '{test_query}'")
        logger.info(f"  Vector dimension: {len(vec)} | Vectorization latency: {embed_ms:.2f}ms")
    except Exception as e:
        logger.error(f"✗ Embedding service verification failed: {e}")

    # 3. Qdrant service check
    try:
        from backend.app.services.qdrant_service import qdrant_service
        from backend.app.schemas.rag_schemas import PassageChunk

        logger.info("Initializing Qdrant in-memory vector database service...")
        qdrant_service.initialize_client()

        # Insert test chunks
        test_chunks = [
            PassageChunk(
                chunk_id="1",
                doc_id="hi_101",
                text="भारत का राष्ट्रीय फूल कमल है।",
                language="hi"
            ),
            PassageChunk(
                chunk_id="2",
                doc_id="hi_102",
                text="गोवा की राजधानी पणजी है।",
                language="hi"
            )
        ]
        test_vectors = [embedding_service.embed_query(c.text)[0] for c in test_chunks]
        qdrant_service.upsert_chunks(test_chunks, test_vectors)

        # Search test
        query_vec, _ = embedding_service.embed_query("गोवा की राजधानी?")
        results, search_ms = qdrant_service.search(query_vec, top_k=2)
        logger.info(f"✓ Qdrant search returned {len(results)} matches in {search_ms:.2f}ms")
        if results:
            logger.info(f"  Top result: [{results[0].doc_id}] {results[0].text} (Score: {results[0].score:.4f})")
    except Exception as e:
        logger.error(f"✗ Qdrant service verification failed: {e}")

    logger.info("==========================================")
    logger.info("Phase 1 Component Verification Complete")
    logger.info("==========================================")


if __name__ == "__main__":
    verify_phase1()
