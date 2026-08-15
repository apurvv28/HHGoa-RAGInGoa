"""
Qdrant Vector DB Service Manager.
Supports local in-memory Qdrant (:memory:) and Qdrant Cloud.
Configures HNSW index parameters for low-latency search (<20ms).
"""

import time
import logging
from typing import Optional, Any
from backend.app.config import settings
from backend.app.schemas.rag_schemas import PassageChunk

logger = logging.getLogger(__name__)


class QdrantService:
    _instance: Optional["QdrantService"] = None

    def __init__(self):
        self.client = None
        self.collection_name = settings.QDRANT_COLLECTION_NAME
        self.vector_dim = settings.VECTOR_DIMENSION

    @classmethod
    def get_instance(cls) -> "QdrantService":
        if cls._instance is None:
            cls._instance = QdrantService()
        return cls._instance

    def initialize_client(self) -> None:
        """Initializes Qdrant client connection."""
        if self.client is not None:
            return

        logger.info(f"Connecting to Qdrant at '{settings.QDRANT_URL}'...")
        start_time = time.perf_counter()

        try:
            from qdrant_client import QdrantClient # type: ignore
            if settings.QDRANT_URL == ":memory:":
                self.client = QdrantClient(":memory:")
            else:
                self.client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
                    timeout=5.0
                )
            
            init_ms = (time.perf_counter() - start_time) * 1000
            logger.info(f"Qdrant client initialized in {init_ms:.2f}ms")
            self.ensure_collection_exists()

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            self.client = None

    def ensure_collection_exists(self) -> None:
        """Ensures the target collection exists with tuned HNSW params."""
        if self.client is None:
            return

        try:
            from qdrant_client.http import models # type: ignore

            collections = self.client.get_collections().collections
            exists = any(c.name == self.collection_name for c in collections)

            if not exists:
                logger.info(f"Creating collection '{self.collection_name}' with vector dimension {self.vector_dim}...")
                
                # Match distance metric
                distance = models.Distance.COSINE
                if settings.DISTANCE_METRIC.lower() == "euclidean":
                    distance = models.Distance.EUCLID
                elif settings.DISTANCE_METRIC.lower() == "dot":
                    distance = models.Distance.DOT

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_dim,
                        distance=distance,
                    ),
                    hnsw_config=models.HnswConfigDiff(
                        m=16,
                        ef_construct=128,
                        on_disk=False,
                    ),
                )
                logger.info(f"Collection '{self.collection_name}' created successfully.")
            else:
                logger.info(f"Collection '{self.collection_name}' already exists.")

        except Exception as e:
            logger.error(f"Error ensuring Qdrant collection: {e}")

    def search(
        self,
        query_vector: list[float],
        top_k: int = 5,
        language_filter: Optional[str] = None
    ) -> tuple[list[PassageChunk], float]:
        """
        Executes ANN vector search against Qdrant collection.
        Returns (list[PassageChunk], search_latency_ms).
        """
        if self.client is None:
            self.initialize_client()

        if self.client is None:
            return [], 0.0

        start_time = time.perf_counter()
        chunks: list[PassageChunk] = []

        try:
            from qdrant_client.http import models # type: ignore

            query_filter = None
            if language_filter:
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="language",
                            match=models.MatchValue(value=language_filter),
                        )
                    ]
                )

            # Perform vector search using query_points (qdrant-client >= 1.10) or search
            if hasattr(self.client, "query_points"):
                res = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                )
                search_results = res.points
            elif hasattr(self.client, "search"):
                search_results = self.client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=top_k,
                    query_filter=query_filter,
                )
            else:
                search_results = []

            for res in search_results:
                payload = res.payload or {}
                chunks.append(
                    PassageChunk(
                        chunk_id=str(res.id),
                        doc_id=payload.get("doc_id", str(res.id)),
                        text=payload.get("text", ""),
                        language=payload.get("language", "en"),
                        score=float(res.score),
                        metadata=payload.get("metadata", {}),
                    )
                )

        except Exception as e:
            logger.error(f"Error during Qdrant search: {e}")

        search_ms = (time.perf_counter() - start_time) * 1000
        return chunks, search_ms

    def upsert_chunks(
        self,
        chunks: list[PassageChunk],
        vectors: list[list[float]]
    ) -> bool:
        """Upserts a batch of passage chunks and vectors to Qdrant."""
        if self.client is None:
            self.initialize_client()

        if self.client is None or not chunks:
            return False

        try:
            from qdrant_client.http import models # type: ignore

            points = []
            for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
                # Ensure integer or string point ID
                try:
                    point_id = int(chunk.chunk_id)
                except ValueError:
                    point_id = i + 1

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=vec,
                        payload={
                            "chunk_id": chunk.chunk_id,
                            "doc_id": chunk.doc_id,
                            "text": chunk.text,
                            "language": chunk.language,
                            "metadata": chunk.metadata,
                        },
                    )
                )

            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            logger.info(f"Successfully upserted {len(points)} chunks into Qdrant.")
            return True
        except Exception as e:
            logger.error(f"Error during Qdrant upsert: {e}")
            return False


# Global singleton instance
qdrant_service = QdrantService.get_instance()
