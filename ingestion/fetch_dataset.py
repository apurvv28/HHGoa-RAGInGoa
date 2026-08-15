"""
Dataset Fetcher & Index Loader for ai4bharat/MSMARCO-XI
Downloads Indic Parquet splits (Hindi, Marathi, Tamil, etc.) directly via HuggingFace Hub
and streams batches using PyArrow for minimal RAM footprint.
"""

import os
import json
import logging
from typing import Any
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

REPO_ID = "ai4bharat/MSMARCO-XI"
DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))


def fetch_msmarco_split(filename: str, language_code: str, max_records: int = 100) -> list[dict[str, Any]]:
    """
    Downloads and parses max_records from a parquet file using PyArrow batch streaming.
    """
    logger.info(f"Downloading {filename} for language '{language_code}'...")
    records: list[dict[str, Any]] = []

    try:
        file_path = hf_hub_download(repo_id=REPO_ID, filename=filename, repo_type="dataset")
        
        # Memory-safe batch streaming using PyArrow
        parquet_file = pq.ParquetFile(file_path)
        batch = next(parquet_file.iter_batches(batch_size=max_records * 2))
        df = batch.to_pandas()
        
        logger.info(f"Streamed {len(df)} batch rows from {filename}. Columns: {df.columns.tolist()}")

        count = 0
        for idx, row in df.iterrows():
            if count >= max_records:
                break

            query_id = str(row.get("query_id") or row.get("id") or f"{language_code}_{idx}")
            query_text = str(row.get("query") or row.get("question") or row.get("Eng_Query") or "")
            
            raw_passages = row.get("passages") or row.get("passage") or {}
            parsed_passages = []

            if isinstance(raw_passages, dict):
                # Safely extract texts array without triggering numpy truth value error
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
                    if isinstance(p, dict):
                        p_text = p.get("passage_text") or p.get("text") or ""
                        is_sel = p.get("is_selected", 0)
                    else:
                        p_text = str(p)
                        is_sel = 1 if p_idx == 0 else 0

                    if p_text.strip():
                        parsed_passages.append({
                            "passage_id": f"p_{query_id}_{p_idx}",
                            "passage_text": p_text.strip(),
                            "is_selected": int(is_sel)
                        })

            if query_text.strip() and parsed_passages:
                records.append({
                    "query_id": query_id,
                    "query": query_text.strip(),
                    "passages": parsed_passages,
                    "language": language_code
                })
                count += 1

        logger.info(f"Successfully processed {len(records)} query-passage records for {language_code}.")
    except Exception as e:
        logger.error(f"Error fetching parquet file {filename}: {e}")

    return records


def build_full_dataset(max_records_per_split: int = 150) -> str:
    """Fetches Hindi & Indic splits and constructs full local benchmark dataset."""
    os.makedirs(DATA_DIR, exist_ok=True)

    all_records: list[dict[str, Any]] = []

    # 1. Hindi Val & Train
    hi_val = fetch_msmarco_split("validation/hinval.parquet", "hi", max_records=max_records_per_split)
    all_records.extend(hi_val)

    output_path = os.path.join(DATA_DIR, "msmarco_xi_dataset.json")
    sample_path = os.path.join(DATA_DIR, "sample_msmarco.json")

    payload = {
        "dataset_name": REPO_ID,
        "record_count": len(all_records),
        "records": all_records
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    if all_records:
        with open(sample_path, "w", encoding="utf-8") as f:
            json.dump({"dataset_name": REPO_ID, "sample_count": min(len(all_records), 20), "samples": all_records[:20]}, f, ensure_ascii=False, indent=2)

    logger.info(f"Full dataset written to {output_path} ({len(all_records)} records).")
    return output_path


if __name__ == "__main__":
    build_full_dataset()
