"""
Offline Vector Indexing Pipeline.
Pre-computes passage embeddings offline using intfloat/multilingual-e5-small
and bulk indexes into Qdrant for sub-100ms query retrieval.
"""

import os
import json
import time
import sys
import logging
from typing import Literal

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service
from backend.app.schemas.rag_schemas import PassageChunk
from ingestion.chunker import MultiStrategyChunker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("index_passages")

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def load_dataset_file() -> tuple[str, list[dict]]:
    """Loads msmarco_xi_dataset.json or sample_msmarco.json as fallback."""
    full_path = os.path.join(DATA_DIR, "msmarco_xi_dataset.json")
    sample_path = os.path.join(DATA_DIR, "sample_msmarco.json")

    records = []
    target_path = full_path

    if os.path.exists(full_path):
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("records") or data.get("samples") or []

    # If msmarco_xi_dataset.json is empty or missing, fallback to sample_msmarco.json
    if not records and os.path.exists(sample_path):
        logger.info(f"msmarco_xi_dataset.json empty or missing. Falling back to {sample_path}...")
        target_path = sample_path
        with open(sample_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        records = data.get("records") or data.get("samples") or []

    if not records:
        raise FileNotFoundError(f"Neither {full_path} nor {sample_path} contains records.")

    logger.info(f"Loaded {len(records)} records from {target_path}.")
    return target_path, records


def index_dataset(
    strategy: Literal["fixed", "semantic", "metadata_aware"] = "metadata_aware",
    batch_size: int = 32
) -> dict:
    """
    Chunks all dataset passages using designated strategy, pre-computes offline embeddings,
    and bulk upserts vectors into Qdrant.
    """
    logger.info(f"Starting offline passage indexing pipeline using strategy='{strategy}'...")
    start_time = time.perf_counter()

    _, records = load_dataset_file()
    if not records:
        logger.warning("No records found to index.")
        return {"status": "empty", "total_chunks": 0}

    # 1. Preload embedding model and initialize Qdrant
    embedding_service.load_model()
    qdrant_service.initialize_client()

    all_chunks: list[PassageChunk] = []

    # 2. Apply strategy chunking to all passages
    for rec in records:
        query_id = rec.get("query_id", "")
        lang = rec.get("language", "hi")
        passages = rec.get("passages", [])

        for p_idx, p in enumerate(passages):
            if isinstance(p, dict):
                p_id = p.get("passage_id") or f"p_{query_id}_{p_idx}"
                p_text = p.get("passage_text") or ""
            else:
                p_id = f"p_{query_id}_{p_idx}"
                p_text = str(p)

            if p_text.strip():
                chunks = MultiStrategyChunker.create_chunks(
                    doc_id=p_id,
                    text=p_text,
                    language=lang,
                    strategy=strategy,
                    query_id=query_id
                )
                all_chunks.extend(chunks)

    logger.info(f"Generated {len(all_chunks)} chunks across {len(records)} query-passage records.")

    # 3. Batch pre-compute passage embeddings offline
    total_chunks = len(all_chunks)
    vectors: list[list[float]] = []

    for i in range(0, total_chunks, batch_size):
        batch_chunks = all_chunks[i : i + batch_size]
        batch_texts = [c.text for c in batch_chunks]
        batch_vectors = embedding_service.embed_passages(batch_texts)
        vectors.extend(batch_vectors)

    # 4. Bulk upsert to Qdrant
    upsert_success = qdrant_service.upsert_chunks(all_chunks, vectors)

    # Save to disk cache for instantaneous auto-seed startup (< 50ms)
    try:
        cache_path = os.path.join(DATA_DIR, "precomputed_vectors.json")
        cache_payload = [
            {
                "chunk": chunk.model_dump(),
                "vector": vec
            }
            for chunk, vec in zip(all_chunks, vectors)
        ]
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_payload, f, ensure_ascii=False)
        logger.info(f"Saved {len(cache_payload)} precomputed vectors to {cache_path}")
    except Exception as e:
        logger.warning(f"Could not save vector cache: {e}")

    total_indexing_ms = (time.perf_counter() - start_time) * 1000

    result = {
        "status": "success" if upsert_success else "failed",
        "strategy": strategy,
        "total_records": len(records),
        "total_chunks": total_chunks,
        "indexing_time_ms": round(total_indexing_ms, 2),
        "vector_dimension": settings.VECTOR_DIMENSION if 'settings' in globals() else 384,
    }

    logger.info(f"Offline indexing complete in {total_indexing_ms:.2f}ms. Total chunks indexed: {total_chunks}")
    return result


if __name__ == "__main__":
    index_dataset()
