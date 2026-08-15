"""
Multi-Strategy Chunking Engine.
Supports 3 swappable chunking strategies:
1. Fixed-size overlapping token/word window chunker
2. Semantic sentence-boundary chunker (with Indic '।' support)
3. Metadata-aware chunker (preserves document & query IDs)
"""

import re
import logging
from typing import Literal
from backend.app.schemas.rag_schemas import PassageChunk

logger = logging.getLogger(__name__)

# Indic and English sentence split pattern (supports '।', '?', '!', '.')
SENTENCE_SPLIT_REGEX = re.compile(r'(?<=[।?!.])\s+')


class MultiStrategyChunker:
    """Provides chunking implementations for RAG indexing."""

    @staticmethod
    def fixed_size_chunk(
        text: str,
        words_per_chunk: int = 80,
        overlap_words: int = 15
    ) -> list[str]:
        """
        Fixed-size chunker with sliding word window overlap.
        """
        words = text.strip().split()
        if not words:
            return []

        if len(words) <= words_per_chunk:
            return [text.strip()]

        chunks = []
        step = words_per_chunk - overlap_words
        if step <= 0:
            step = words_per_chunk

        for i in range(0, len(words), step):
            chunk_words = words[i : i + words_per_chunk]
            chunk_str = " ".join(chunk_words).strip()
            if chunk_str:
                chunks.append(chunk_str)

        return chunks

    @staticmethod
    def semantic_chunk(
        text: str,
        target_words: int = 100
    ) -> list[str]:
        """
        Semantic chunker splitting on natural sentence boundaries (Hindi '।' & English '.').
        Aggregates sentences until target word count is reached.
        """
        sentences = [s.strip() for s in SENTENCE_SPLIT_REGEX.split(text.strip()) if s.strip()]
        if not sentences:
            return [text.strip()] if text.strip() else []

        chunks = []
        current_chunk_sentences = []
        current_word_count = 0

        for sentence in sentences:
            sentence_words = len(sentence.split())
            if current_word_count + sentence_words > target_words and current_chunk_sentences:
                chunks.append(" ".join(current_chunk_sentences))
                current_chunk_sentences = [sentence]
                current_word_count = sentence_words
            else:
                current_chunk_sentences.append(sentence)
                current_word_count += sentence_words

        if current_chunk_sentences:
            chunks.append(" ".join(current_chunk_sentences))

        return chunks

    @classmethod
    def create_chunks(
        cls,
        doc_id: str,
        text: str,
        language: str = "hi",
        strategy: Literal["fixed", "semantic", "metadata_aware"] = "metadata_aware",
        query_id: str = ""
    ) -> list[PassageChunk]:
        """
        Creates metadata-enriched PassageChunk objects using designated strategy.
        """
        if strategy == "fixed":
            text_chunks = cls.fixed_size_chunk(text, words_per_chunk=80, overlap_words=15)
        elif strategy == "semantic":
            text_chunks = cls.semantic_chunk(text, target_words=100)
        else:  # metadata_aware (hybrid semantic with full metadata binding)
            text_chunks = cls.semantic_chunk(text, target_words=90)

        total_chunks = len(text_chunks)
        passage_chunks: list[PassageChunk] = []

        for idx, chunk_text in enumerate(text_chunks):
            chunk_id = f"{doc_id}_c{idx}"
            passage_chunks.append(
                PassageChunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    text=chunk_text,
                    language=language,
                    score=0.0,
                    metadata={
                        "query_id": query_id,
                        "chunk_index": idx,
                        "total_chunks": total_chunks,
                        "strategy": strategy,
                        "language": language,
                    }
                )
            )

        return passage_chunks
