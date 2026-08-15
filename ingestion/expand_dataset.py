"""
Expand Dataset Script
Fetches up to 600 records from ai4bharat/MSMARCO-XI Hindi validation set,
merges with existing msmarco_xi_dataset.json, and rebuilds precomputed_vectors.json cache.
"""

import os
import sys
import json
import logging
import time

# Ensure project root is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("expand_dataset")

DATA_DIR = os.path.join(ROOT, "data")
DATASET_PATH = os.path.join(DATA_DIR, "msmarco_xi_dataset.json")
CACHE_PATH = os.path.join(DATA_DIR, "precomputed_vectors.json")

TARGET_RECORDS = 600  # Target total records


def main():
    # ── Step 1: Load existing dataset ──────────────────────────────────────
    logger.info("Loading existing dataset...")
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    existing_records = dataset.get("records", [])
    existing_ids = {r["query_id"] for r in existing_records}
    logger.info(f"Existing records: {len(existing_records)}")

    needed = TARGET_RECORDS - len(existing_records)
    if needed <= 0:
        logger.info(f"Already have {len(existing_records)} records. Nothing to do.")
        return

    logger.info(f"Need {needed} more records to reach {TARGET_RECORDS} total.")

    # ── Step 2: Fetch more records from HuggingFace ────────────────────────
    logger.info("Fetching more records from ai4bharat/MSMARCO-XI...")
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    REPO_ID = "ai4bharat/MSMARCO-XI"
    file_path = hf_hub_download(repo_id=REPO_ID, filename="validation/hinval.parquet", repo_type="dataset")
    
    parquet_file = pq.ParquetFile(file_path)
    new_records = []
    
    # Stream in batches of 1000 until we have enough
    for batch in parquet_file.iter_batches(batch_size=1000):
        if len(new_records) >= needed:
            break
        df = batch.to_pandas()
        logger.info(f"Processing batch of {len(df)} rows...")

        for idx, row in df.iterrows():
            if len(new_records) >= needed:
                break

            query_id = str(row.get("query_id") or row.get("id") or f"hi_{idx}")
            if query_id in existing_ids:
                continue  # skip duplicates

            query_text = str(row.get("query") or row.get("question") or row.get("Eng_Query") or "").strip()
            raw_passages = row.get("passages") or {}
            parsed_passages = []

            if isinstance(raw_passages, dict):
                if "Translated_passages" in raw_passages and len(raw_passages["Translated_passages"]) > 0:
                    texts = raw_passages["Translated_passages"]
                elif "passage_text" in raw_passages and len(raw_passages["passage_text"]) > 0:
                    texts = raw_passages["passage_text"]
                elif "English_passages" in raw_passages and len(raw_passages["English_passages"]) > 0:
                    texts = raw_passages["English_passages"]
                else:
                    texts = []

                selected_flags = raw_passages.get("is_selected", [])
                for p_idx, text_val in enumerate(texts):
                    p_text = str(text_val).strip()
                    try:
                        is_sel = int(selected_flags[p_idx]) if (hasattr(selected_flags, "__len__") and p_idx < len(selected_flags)) else 0
                    except (IndexError, ValueError, TypeError):
                        is_sel = 1 if p_idx == 0 else 0
                    if p_text:
                        parsed_passages.append({
                            "passage_id": f"p_{query_id}_{p_idx}",
                            "passage_text": p_text,
                            "is_selected": is_sel
                        })

            elif isinstance(raw_passages, list):
                for p_idx, p in enumerate(raw_passages):
                    p_text = (p.get("passage_text") or p.get("text") or str(p)).strip() if isinstance(p, dict) else str(p).strip()
                    is_sel = p.get("is_selected", 0) if isinstance(p, dict) else (1 if p_idx == 0 else 0)
                    if p_text:
                        parsed_passages.append({
                            "passage_id": f"p_{query_id}_{p_idx}",
                            "passage_text": p_text,
                            "is_selected": int(is_sel)
                        })

            if query_text and parsed_passages:
                new_records.append({
                    "query_id": query_id,
                    "query": query_text,
                    "passages": parsed_passages,
                    "language": "hi"
                })
                existing_ids.add(query_id)

    logger.info(f"Fetched {len(new_records)} new records.")

    # ── Step 3: Merge and save ─────────────────────────────────────────────
    all_records = existing_records + new_records
    dataset["records"] = all_records
    dataset["record_count"] = len(all_records)

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    logger.info(f"Dataset expanded to {len(all_records)} records → {DATASET_PATH}")

    # ── Step 4: Re-index everything into precomputed_vectors.json ──────────
    logger.info("Re-indexing all records into precomputed_vectors.json...")
    from ingestion.index_passages import index_dataset
    index_dataset(strategy="metadata_aware")
    logger.info("Re-indexing complete! Restart uvicorn to load the new cache.")


if __name__ == "__main__":
    start = time.time()
    main()
    logger.info(f"Total time: {time.time() - start:.1f}s")
