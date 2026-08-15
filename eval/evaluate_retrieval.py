"""
Recall@k Benchmarking Harness for Multi-Strategy Chunking & Retrieval.
Evaluates Recall@1, Recall@5, Recall@10, and average retrieval latency across:
1. Fixed-size overlapping chunking
2. Semantic sentence-boundary chunking
3. Metadata-aware structure-preserving chunking
"""

import os
import sys
import json
import time
import logging
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.services.embedding_service import embedding_service
from backend.app.services.qdrant_service import qdrant_service
from ingestion.index_passages import index_dataset, load_dataset_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("evaluate_retrieval")


def evaluate_chunking_strategy(strategy_name: str) -> dict[str, Any]:
    """Indexes dataset using strategy and computes Recall@1, Recall@5, Recall@10, and avg latency."""
    logger.info(f"Evaluating strategy: '{strategy_name}'...")
    
    # Re-index collection with target strategy
    index_res = index_dataset(strategy=strategy_name)

    _, records = load_dataset_file()
    if not records:
        return {"strategy": strategy_name, "error": "No records"}

    r1_hits = 0
    r5_hits = 0
    r10_hits = 0
    total_queries = 0
    total_latency_ms = 0.0

    for rec in records:
        query_text = rec.get("query", "").strip()
        passages = rec.get("passages", [])
        lang = rec.get("language", "hi")

        if not query_text or not passages:
            continue

        # Find ground-truth passage texts
        ground_truth_texts = []
        for p in passages:
            if isinstance(p, dict):
                if p.get("is_selected", 0) == 1:
                    ground_truth_texts.append(p.get("passage_text", "").strip())
            else:
                ground_truth_texts.append(str(p).strip())

        if not ground_truth_texts:
            continue

        total_queries += 1

        # Perform query vectorization & Qdrant search
        start_time = time.perf_counter()
        query_vec, embed_ms = embedding_service.embed_query(query_text)
        retrieved_chunks, qdrant_ms = qdrant_service.search(query_vec, top_k=10, language_filter=lang)
        latency_ms = (time.perf_counter() - start_time) * 1000
        total_latency_ms += latency_ms

        retrieved_texts = [c.text for c in retrieved_chunks]

        # Check recall at k=1, 5, 10
        def hits_at_k(k: int) -> bool:
            top_k_retrieved = retrieved_texts[:k]
            for gt in ground_truth_texts:
                for ret in top_k_retrieved:
                    if gt in ret or ret in gt or gt[:30] in ret:
                        return True
            return False

        if hits_at_k(1):
            r1_hits += 1
        if hits_at_k(5):
            r5_hits += 1
        if hits_at_k(10):
            r10_hits += 1

    r1 = round((r1_hits / total_queries) * 100, 2) if total_queries else 0.0
    r5 = round((r5_hits / total_queries) * 100, 2) if total_queries else 0.0
    r10 = round((r10_hits / total_queries) * 100, 2) if total_queries else 0.0
    avg_lat = round(total_latency_ms / total_queries, 2) if total_queries else 0.0

    metrics = {
        "strategy": strategy_name,
        "total_queries": total_queries,
        "total_indexed_chunks": index_res.get("total_chunks", 0),
        "recall_at_1": f"{r1}%",
        "recall_at_5": f"{r5}%",
        "recall_at_10": f"{r10}%",
        "avg_retrieval_latency_ms": f"{avg_lat} ms",
        "r1_val": r1,
        "r5_val": r5,
        "r10_val": r10,
        "avg_lat_val": avg_lat,
    }

    logger.info(f"Strategy '{strategy_name}' Results: R@1={r1}%, R@5={r5}%, R@10={r10}%, Avg Latency={avg_lat}ms")
    return metrics


def run_full_evaluation() -> list[dict[str, Any]]:
    """Runs evaluation across all 3 strategies and saves benchmark_results.json."""
    logger.info("=============================================")
    logger.info("Starting Multi-Strategy Recall@k Benchmarking")
    logger.info("=============================================")

    strategies = ["fixed", "semantic", "metadata_aware"]
    results = []

    for strat in strategies:
        res = evaluate_chunking_strategy(strat)
        results.append(res)

    # Print strategy matrix table
    logger.info("\n--- STRATEGY COMPARISON MATRIX ---")
    logger.info(f"{'Strategy':<18} | {'Recall@1':<10} | {'Recall@5':<10} | {'Recall@10':<10} | {'Avg Latency':<12}")
    logger.info("-" * 70)
    for r in results:
        logger.info(f"{r['strategy']:<18} | {r['recall_at_1']:<10} | {r['recall_at_5']:<10} | {r['recall_at_10']:<10} | {r['avg_retrieval_latency_ms']:<12}")
    logger.info("-" * 70)

    # Save benchmark results artifact
    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "benchmark_results.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"Saved benchmark results to {output_path}")
    return results


if __name__ == "__main__":
    run_full_evaluation()
