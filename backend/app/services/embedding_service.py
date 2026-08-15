"""
Singleton Indic Embedding Service.
Pre-loads intfloat/multilingual-e5-small in memory at application startup to achieve sub-20ms query vectorization.
"""

import time
import logging
from typing import Optional
from backend.app.config import settings

logger = logging.getLogger(__name__)


class IndicEmbeddingService:
    _instance: Optional["IndicEmbeddingService"] = None

    def __init__(self, model_name: str = settings.EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.model = None
        self.vector_dim = settings.VECTOR_DIMENSION

    @classmethod
    def get_instance(cls) -> "IndicEmbeddingService":
        if cls._instance is None:
            cls._instance = IndicEmbeddingService()
        return cls._instance

    def load_model(self) -> None:
        """Loads the SentenceTransformer model into memory."""
        if self.model is not None:
            return

        logger.info(f"Loading Indic embedding model: {self.model_name}...")
        start_time = time.perf_counter()

        try:
            from sentence_transformers import SentenceTransformer # type: ignore
            self.model = SentenceTransformer(self.model_name)
            load_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Indic embedding model preloaded successfully in {load_ms:.2f}ms")
        except Exception as e:
            logger.error(f"Failed to load sentence-transformers model '{self.model_name}': {e}")
            self.model = None

    def embed_query(self, query: str) -> tuple[list[float], float]:
        """
        Embeds a single search query text and returns (vector, latency_ms).
        For E5 models, prefixes query with 'query: ' for optimal performance.
        """
        if self.model is None:
            self.load_model()

        start_time = time.perf_counter()

        # E5 model convention: prepend 'query: ' for asymmetric retrieval queries
        formatted_query = query
        if "e5" in self.model_name.lower():
            formatted_query = f"query: {query}"

        if self.model is not None:
            embedding = self.model.encode(formatted_query, normalize_embeddings=True)
            vector = embedding.tolist()
        else:
            # Fallback zero-vector if model fails to load
            logger.warning("Embedding model not ready. Returning dummy zero vector.")
            vector = [0.0] * self.vector_dim

        latency_ms = (time.perf_counter() - start_time) * 1000
        return vector, latency_ms

    def embed_passages(self, passages: list[str]) -> list[list[float]]:
        """
        Batch embeds passages (pre-computation for indexing).
        For E5 models, prefixes passages with 'passage: '.
        """
        if self.model is None:
            self.load_model()

        formatted_passages = passages
        if "e5" in self.model_name.lower():
            formatted_passages = [f"passage: {p}" for p in passages]

        if self.model is not None:
            embeddings = self.model.encode(formatted_passages, batch_size=32, normalize_embeddings=True)
            return embeddings.tolist()
        else:
            return [[0.0] * self.vector_dim for _ in passages]


# Global singleton instance
embedding_service = IndicEmbeddingService.get_instance()
