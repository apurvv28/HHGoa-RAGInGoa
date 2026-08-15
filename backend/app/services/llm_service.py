"""
Groq LLM Inference & Guardrail Service.
Provides fast inference via Groq API (llama-3.1-8b-instant) for answer generation,
context relevance grading, and hallucination grounding validation.
"""

import time
import logging
from typing import Tuple, Optional, List
import httpx
from backend.app.config import settings
from backend.app.schemas.rag_schemas import PassageChunk

logger = logging.getLogger(__name__)


class GroqLLMService:
    """Service wrapper for Groq LLM inference and guardrail checks."""

    GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str = settings.GROQ_API_KEY, model: str = settings.GROQ_MODEL):
        self.api_key = api_key
        self.model = model

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def generate_response(
        self,
        query: str,
        context_chunks: list[PassageChunk],
        language: str = "hi"
    ) -> Tuple[str, float]:
        """
        Generates grounded answer from retrieved context chunks.
        Returns (answer_text, generation_latency_ms).
        """
        start_time = time.perf_counter()

        if not context_chunks:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return "अपर्याप्त जानकारी। दिए गए संदर्भ के आधार पर इस प्रश्न का उत्तर नहीं दिया जा सकता।", latency_ms

        context_str = "\n\n".join([f"[{i+1}] {c.text}" for i, c in enumerate(context_chunks)])

        # Prompt tuned for strict grounding and Indic response
        system_prompt = (
            "You are an accurate, helpful AI assistant. Answer the user question strictly using ONLY the provided context passages below.\n"
            "If the answer cannot be directly derived from the context, reply with: 'अपर्याप्त जानकारी: दिए गए संदर्भ में उत्तर मौजूद नहीं है।'\n"
            "Keep the response concise (2-4 sentences max). Respond in the language of the query."
        )

        user_prompt = f"Context:\n{context_str}\n\nUser Question: {query}\n\nAnswer:"

        if not self.api_key or not self.api_key.strip():
            # Fallback deterministic generator if GROQ_API_KEY is not set
            logger.warning("GROQ_API_KEY not set. Operating in fallback generation mode.")
            top_chunk = context_chunks[0]
            answer = f"संदर्भ के अनुसार: {top_chunk.text}"
            latency_ms = (time.perf_counter() - start_time) * 1000
            return answer, latency_ms

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 250,
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(self.GROQ_API_URL, headers=self._get_headers(), json=payload)
                response.raise_for_status()
                res_data = response.json()
                answer = res_data["choices"][0]["message"]["content"].strip()
                latency_ms = (time.perf_counter() - start_time) * 1000
                return answer, latency_ms
        except Exception as e:
            logger.error(f"Groq LLM generation call failed: {e}")
            top_chunk = context_chunks[0]
            fallback_answer = f"संदर्भ: {top_chunk.text}"
            latency_ms = (time.perf_counter() - start_time) * 1000
            return fallback_answer, latency_ms

    async def grade_context(self, query: str, chunks: list[PassageChunk]) -> Tuple[list[PassageChunk], float]:
        """
        Grades relevance of retrieved chunks against user query.
        Returns (relevant_chunks, grade_latency_ms).
        """
        start_time = time.perf_counter()
        if not chunks:
            return [], 0.0

        # Filter out chunks with very low similarity scores or empty text
        relevant_chunks = [c for c in chunks if c.score >= 0.25 and c.text.strip()]
        grade_ms = (time.perf_counter() - start_time) * 1000
        return relevant_chunks if relevant_chunks else chunks[:1], grade_ms

    async def validate_grounding(self, query: str, answer: str, context_chunks: list[PassageChunk]) -> Tuple[bool, float]:
        """
        Verifies answer is entailed by context (anti-hallucination check).
        Returns (is_grounded, validation_latency_ms).
        """
        start_time = time.perf_counter()

        if "अपर्याप्त जानकारी" in answer:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return True, latency_ms

        if not context_chunks:
            latency_ms = (time.perf_counter() - start_time) * 1000
            return False, latency_ms

        # Fast substring/overlap check for baseline anti-hallucination validation
        context_combined = " ".join([c.text for c in context_chunks]).lower()
        answer_words = [w for w in answer.lower().split() if len(w) > 3]

        matches = sum(1 for w in answer_words if w in context_combined)
        is_grounded = (matches / len(answer_words) >= 0.4) if answer_words else True

        latency_ms = (time.perf_counter() - start_time) * 1000
        return is_grounded, latency_ms


llm_service = GroqLLMService()
