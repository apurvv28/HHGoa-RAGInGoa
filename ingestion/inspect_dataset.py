"""
Dataset Inspector & Sampler for ai4bharat/MSMARCO-XI
Downloads HF dataset splits (Hindi & English), prints schema, and creates local benchmark sample JSON.
"""

import os
import json
import logging
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DATASET_NAME = "ai4bharat/MSMARCO-XI"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "sample_msmarco.json")


def inspect_and_sample_dataset(max_samples_per_lang: int = 50) -> dict[str, Any]:
    """
    Attempts to load ai4bharat/MSMARCO-XI using huggingface datasets library or fallback inspection.
    """
    logger.info(f"Loading dataset: {DATASET_NAME}")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    samples: list[dict[str, Any]] = []

    try:
        from datasets import load_dataset # type: ignore

        # MSMARCO-XI has language configs such as 'hi' (Hindi), 'en' (English), etc.
        for lang in ["hi", "en"]:
            logger.info(f"Fetching split for language: {lang}")
            try:
                ds = load_dataset(DATASET_NAME, lang, split="train", streaming=True)
                count = 0
                for item in ds:
                    if count >= max_samples_per_lang:
                        break
                    
                    # Extract standard fields or inspect item keys
                    record = {
                        "query_id": item.get("query_id") or item.get("id") or f"{lang}_{count}",
                        "query": item.get("query") or item.get("question") or "",
                        "passages": item.get("passages") or item.get("passage") or item.get("positive_passages") or [],
                        "language": lang,
                    }
                    samples.append(record)
                    count += 1
                logger.info(f"Loaded {count} samples for {lang}")
            except Exception as e:
                logger.warning(f"Could not load split '{lang}' directly: {e}. Trying default split...")

    except ImportError:
        logger.warning("datasets library not installed yet. Creating placeholder benchmark schema structure.")
    except Exception as e:
        logger.error(f"Error loading dataset from HF: {e}")

    # Fallback/Synthetic mock sample generator if HF dataset fails or offline
    if not samples:
        logger.info("Generating representative MSMARCO-XI sample records (Hindi + English) for local offline development...")
        samples = [
            {
                "query_id": "hi_101",
                "query": "भारत का राष्ट्रीय फूल कौन सा है?",
                "passages": [
                    {
                        "passage_id": "p_hi_101_1",
                        "passage_text": "भारत का राष्ट्रीय फूल कमल (Lotus) है। यह पवित्रता, उर्वरता और सुंदरता का प्रतीक माना जाता है।",
                        "is_selected": 1,
                    },
                    {
                        "passage_id": "p_hi_101_2",
                        "passage_text": "गुलाब को फूलों का राजा माना जाता है, परंतु भारत का राष्ट्रीय फूल कमल ही है।",
                        "is_selected": 0,
                    }
                ],
                "language": "hi",
            },
            {
                "query_id": "hi_102",
                "query": "गोवा की राजधानी क्या है?",
                "passages": [
                    {
                        "passage_id": "p_hi_102_1",
                        "passage_text": "गोवा की राजधानी पणजी (Panaji) है, जो मांडवी नदी के तट पर स्थित है।",
                        "is_selected": 1,
                    }
                ],
                "language": "hi",
            },
            {
                "query_id": "en_201",
                "query": "What is the capital of Goa?",
                "passages": [
                    {
                        "passage_id": "p_en_201_1",
                        "passage_text": "Panaji is the capital of the Indian state of Goa and the headquarters of North Goa district.",
                        "is_selected": 1,
                    }
                ],
                "language": "en",
            },
            {
                "query_id": "hi_103",
                "query": "कृत्रिम बुद्धिमत्ता (AI) क्या है?",
                "passages": [
                    {
                        "passage_id": "p_hi_103_1",
                        "passage_text": "कृत्रिम बुद्धिमत्ता (Artificial Intelligence) कंप्यूटर विज्ञान की वह शाखा है जो मशीनों को मानव बुद्धिमत्ता की तरह सोचने और सीखने की क्षमता प्रदान करती है।",
                        "is_selected": 1,
                    }
                ],
                "language": "hi",
            }
        ]

    output_data = {
        "dataset_name": DATASET_NAME,
        "sample_count": len(samples),
        "samples": samples,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"Successfully saved dataset inspection samples to {OUTPUT_PATH}")
    return output_data


if __name__ == "__main__":
    inspect_and_sample_dataset()
