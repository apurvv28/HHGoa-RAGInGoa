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

        lang_lower = (language or "hi").lower()
        is_english = lang_lower.startswith("en") or (all(ord(c) < 128 for c in query.strip()[:30]) and not any(k in query.lower() for k in ["kya", "hai", "kaise", "kab", "kahan"]))
        is_marathi = lang_lower.startswith("mr")

        if not context_chunks:
            latency_ms = (time.perf_counter() - start_time) * 1000
            if is_english:
                return "Insufficient context. The answer could not be determined from the provided passages.", latency_ms
            elif is_marathi:
                return "अपुरा संदर्भ. दिलेल्या संदर्भाच्या आधारे या प्रश्नाचे उत्तर देता येत नाही.", latency_ms
            else:
                return "अपर्याप्त जानकारी। दिए गए संदर्भ के आधार पर इस प्रश्न का उत्तर नहीं दिया जा सकता।", latency_ms

        context_str = "\n\n".join([f"[{i+1}] {c.text}" for i, c in enumerate(context_chunks)])

        # Prompt tuned for strict grounding, multi-script Indic matching, and safety rules
        system_prompt = (
            "You are an accurate, helpful multilingual AI assistant.\n"
            "CRITICAL MANDATE 1: You MUST answer the user in the EXACT SAME language and script as the User Question.\n"
            "- If asked in English, answer ONLY in English.\n"
            "- If asked in Marathi, answer ONLY in Marathi (Devanagari script).\n"
            "- If asked in Hindi, answer ONLY in Hindi (Devanagari script).\n"
            "- If asked in Hinglish (Hindi in Roman/Latin script), answer in Hinglish.\n"
            "- If asked in Bengali, Tamil, Telugu, Gujarati, or any other Indic language, answer in that exact language.\n\n"
            "SAFETY RULE: NEVER assist with dangerous, illegal, explosive, or weapon-related queries (like making a bomb). If asked about dangerous topics, refuse politely.\n"
            "RELEVANCE RULE: Do NOT confuse unrelated topics (e.g. food dishes like bibimbap) with explosives, weapons, or dangerous materials.\n"
            "CITATION RULE: NEVER write internal reference numbers like 'passage [1]', 'पैसेज [1]', or '[1]' in your text response. Write naturally.\n\n"
            "FIRST, try to answer using ONLY the provided context passages below.\n"
            "If the context passages do NOT contain the answer, answer accurately in the user's requested language based on factual knowledge.\n"
            "Keep the response concise (2-4 sentences max)."
        )

        user_prompt = f"Target Language Code: {language}\nContext Passages:\n{context_str}\n\nUser Question: {query}\n\nAnswer:"

        if not self.api_key or not self.api_key.strip():
            # Fallback deterministic generator if GROQ_API_KEY is not set
            logger.warning("GROQ_API_KEY not set. Operating in fallback generation mode.")
            top_chunk = context_chunks[0]
            if is_english:
                answer = f"According to context: {top_chunk.text}"
            elif is_marathi:
                answer = f"संदर्भाच्या आधारे: {top_chunk.text}"
            else:
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
            if is_english:
                fallback_answer = f"Context: {top_chunk.text}"
            elif is_marathi:
                fallback_answer = f"संदर्भ: {top_chunk.text}"
            else:
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
        # Use 0.15 threshold — low enough for cross-script Hinglish/Hindi queries
        relevant_chunks = [c for c in chunks if c.score >= 0.15 and c.text.strip()]
        grade_ms = (time.perf_counter() - start_time) * 1000
        # Always pass at least the top chunk so generate_response has context
        return relevant_chunks if relevant_chunks else chunks, grade_ms

    async def validate_grounding(self, query: str, answer: str, context_chunks: list[PassageChunk]) -> Tuple[bool, float]:
        """
        Verifies answer is entailed by context (anti-hallucination check).
        Uses the comprehensive check_hallucination function from guardrails module.
        Returns (is_grounded, validation_latency_ms).
        """
        start_time = time.perf_counter()
        from backend.app.engine.guardrails import check_hallucination
        is_grounded, reason = check_hallucination(answer, context_chunks)
        logger.info(f"Grounding validation: {reason}")
        latency_ms = (time.perf_counter() - start_time) * 1000
        return is_grounded, latency_ms


llm_service = GroqLLMService()
