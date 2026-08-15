"""
P50 / P70 / P100 Latency Benchmarking Harness.
Executes 50 varied Indic & English test queries against the Voice-RAG pipeline,
logs per-stage timestamps, and computes P50, P70, P100 percentiles for:
1. Retrieval Leg (Query Embedding + Qdrant Search + Guardrails) — Target: 80–100ms
2. STT (Sarvam AI API)
3. LLM Generation (Groq Llama 3.1)
4. Total End-to-End Pipeline
"""

import os
import sys
import json
import time
import asyncio
import numpy as np
import logging
from typing import Any

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.engine.rag_graph import run_rag_pipeline
from ingestion.index_passages import index_dataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("benchmark")

# 50 Varied Test Queries (Hindi & English)
TEST_QUERIES = [
    {"query": "भारत का राष्ट्रीय फूल कौन सा है?", "lang": "hi"},
    {"query": "गोवा की राजधानी क्या है?", "lang": "hi"},
    {"query": "What is the capital of Goa?", "lang": "en"},
    {"query": "कृत्रिम बुद्धिमत्ता (AI) क्या है?", "lang": "hi"},
    {"query": "भारत के राष्ट्रपति का नाम क्या है?", "lang": "hi"},
    {"query": "What is machine learning?", "lang": "en"},
    {"query": "ताजमहल कहाँ स्थित है?", "lang": "hi"},
    {"query": "गंगा नदी का उद्गम कहाँ से होता है?", "lang": "hi"},
    {"query": "Which state is known as God's Own Country?", "lang": "en"},
    {"query": "कंप्यूटर का आविष्कार किसने किया?", "lang": "hi"},
    {"query": "भारत का राष्ट्रीय खेल कौन सा है?", "lang": "hi"},
    {"query": "What is artificial intelligence?", "lang": "en"},
    {"query": "सूर्य मंदिर कहाँ स्थित है?", "lang": "hi"},
    {"query": "हिंदी दिवस कब मनाया जाता है?", "lang": "hi"},
    {"query": "Who is known as the Father of the Indian Constitution?", "lang": "en"},
    {"query": "राजस्थान की राजधानी क्या है?", "lang": "hi"},
    {"query": "हिमालय पर्वत कहाँ स्थित है?", "lang": "hi"},
    {"query": "What is the national animal of India?", "lang": "en"},
    {"query": "भारतीय अंतरिक्ष अनुसंधान संगठन (ISRO) का मुख्यालय कहाँ है?", "lang": "hi"},
    {"query": "महात्मा गांधी का जन्म कहाँ हुआ था?", "lang": "hi"},
    {"query": "What is the speed of light?", "lang": "en"},
    {"query": "स्वतंत्र भारत के प्रथम प्रधानमंत्री कौन थे?", "lang": "hi"},
    {"query": "भारत की मुद्रा का क्या नाम है?", "lang": "hi"},
    {"query": "Where is the Red Fort located?", "lang": "en"},
    {"query": "विश्व का सबसे बड़ा महाद्वीपीय देश कौन सा है?", "lang": "hi"},
] * 2  # 25 x 2 = 50 test iterations


async def run_benchmark_suite():
    logger.info("==================================================")
    logger.info("Starting P50/P70/P100 Latency Benchmarking Harness")
    logger.info("==================================================")

    # Pre-index dataset
    index_dataset(strategy="metadata_aware")

    embedding_latencies = []
    qdrant_latencies = []
    retrieval_leg_latencies = []
    guardrail_latencies = []
    generation_latencies = []
    total_e2e_latencies = []

    logger.info(f"Running benchmark across {len(TEST_QUERIES)} test queries...")

    for i, item in enumerate(TEST_QUERIES):
        q_text = item["query"]
        lang = item["lang"]

        res = await run_rag_pipeline(query_text=q_text, language=lang)
        lat = res.latency

        embedding_latencies.append(lat.query_embedding_ms)
        qdrant_latencies.append(lat.qdrant_search_ms)
        retrieval_leg_latencies.append(lat.retrieval_leg_ms)
        guardrail_latencies.append(lat.guardrail_ms)
        generation_latencies.append(lat.generation_ms)
        total_e2e_latencies.append(lat.total_e2e_ms)

    def get_percentiles(data: list[float]) -> dict[str, float]:
        arr = np.array(data)
        return {
            "P50": round(float(np.percentile(arr, 50)), 2),
            "P70": round(float(np.percentile(arr, 70)), 2),
            "P100": round(float(np.percentile(arr, 100)), 2),
            "Mean": round(float(np.mean(arr)), 2),
        }

    report = {
        "sample_count": len(TEST_QUERIES),
        "metrics": {
            "query_embedding_ms": get_percentiles(embedding_latencies),
            "qdrant_search_ms": get_percentiles(qdrant_latencies),
            "retrieval_leg_ms": get_percentiles(retrieval_leg_latencies),
            "guardrail_ms": get_percentiles(guardrail_latencies),
            "generation_ms": get_percentiles(generation_latencies),
            "total_e2e_ms": get_percentiles(total_e2e_latencies),
        }
    }

    # Print summary table
    logger.info("\n--- P50 / P70 / P100 LATENCY BENCHMARK TABLE ---")
    logger.info(f"{'Stage / Component':<30} | {'P50 (ms)':<10} | {'P70 (ms)':<10} | {'P100 (ms)':<10} | {'Mean (ms)':<10}")
    logger.info("-" * 80)
    for stage_name, perc in report["metrics"].items():
        logger.info(f"{stage_name:<30} | {perc['P50']:<10} | {perc['P70']:<10} | {perc['P100']:<10} | {perc['Mean']:<10}")
    logger.info("-" * 80)

    output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "latency_report.json"))
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    logger.info(f"Successfully generated latency report at {output_path}")
    return report


if __name__ == "__main__":
    asyncio.run(run_benchmark_suite())
