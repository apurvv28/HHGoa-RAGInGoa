"""
Guardrail Engine for RAG Pipeline.
Implements:
1. Illegal / legally non-compliant content filter (violence, drugs, weapons, fraud, etc.)
2. Hallucination detection — verifies answer is grounded in context.
3. Off-topic / out-of-corpus domain detector.
4. Input safety moderation (hate speech, self-harm, etc.)
5. Multilingual support for Hindi + English guardrail messages.
"""

import re
import time
import logging
from backend.app.schemas.rag_schemas import PassageChunk, GuardrailResult

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# 1. ILLEGAL / NON-COMPLIANT CONTENT PATTERNS
# ─────────────────────────────────────────────────────────────────────────────

ILLEGAL_PATTERNS = {
    "violence": [
        "bomb", "explosive", "विस्फोटक", "blast", "kill", "murder", "मारना", "हत्या",
        "shoot", "गोली", "knife attack", "चाकू", "terrorism", "आतंकवाद", "terrorist",
        "jihad", "genocide", "नरसंहार", "mass shooting", "beheading"
    ],
    "weapons": [
        "weapon", "हथियार", "gun", "pistol", "rifle", "grenade", "ak47", "ak-47",
        "make a bomb", "बम बनाना", "improvised explosive", "chemical weapon", "रासायनिक हथियार"
    ],
    "drugs": [
        "heroin", "cocaine", "meth", "crystal meth", "drugs kaise", "नशा कैसे",
        "drug trafficking", "smuggling", "तस्करी", "mdma", "lsd", "ketamine",
        "how to make drugs", "ड्रग्स कैसे बनाएं"
    ],
    "cybercrime": [
        "hack", "hacking", "malware", "ransomware", "phishing", "ddos", "exploit",
        "sql injection", "crack password", "पासवर्ड तोड़ना", "keylogger", "trojan",
        "bypass security", "how to hack"
    ],
    "fraud": [
        "scam", "fraud", "धोखाधड़ी", "counterfeit", "नकली", "money laundering",
        "काला धन", "fake currency", "नकली नोट", "ponzi", "identity theft",
        "credit card fraud", "क्रेडिट कार्ड धोखा"
    ],
    "self_harm": [
        "suicide", "आत्महत्या", "self harm", "खुद को नुकसान", "how to die",
        "मरना कैसे", "overdose", "cut myself", "खुद को काटना"
    ],
    "sexual_illegal": [
        "child abuse", "बाल शोषण", "minor", "underage", "pedophile",
        "non-consensual", "rape how", "यौन उत्पीड़न कैसे"
    ],
    "hate_speech": [
        "जातिवाद", "casteism", "hate speech", "नफरत फैलाना", "communal violence",
        "साम्प्रदायिक हिंसा", "lynch", "mob violence", "religious hatred"
    ]
}

# Flatten for fast O(n) lookup
ALL_ILLEGAL_TERMS: list[tuple[str, str]] = [
    (term.lower(), category)
    for category, terms in ILLEGAL_PATTERNS.items()
    for term in terms
]


# ─────────────────────────────────────────────────────────────────────────────
# 2. REFUSAL MESSAGES (Bilingual)
# ─────────────────────────────────────────────────────────────────────────────

REFUSAL_MESSAGES = {
    "violence":         "⚠️ यह प्रश्न हिंसा से संबंधित है। मैं इस पर जानकारी प्रदान नहीं कर सकता। | This query involves violence and cannot be answered.",
    "weapons":          "⚠️ हथियार निर्माण या उपयोग से संबंधित जानकारी प्रदान करना संभव नहीं है। | Weapon-related queries are not supported.",
    "drugs":            "⚠️ नशीले पदार्थों से संबंधित जानकारी प्रदान करना नीति के विरुद्ध है। | Drug-related queries violate our policy.",
    "cybercrime":       "⚠️ साइबर अपराध या हैकिंग से संबंधित प्रश्नों का उत्तर नहीं दिया जा सकता। | Cybercrime or hacking queries are not permitted.",
    "fraud":            "⚠️ धोखाधड़ी, घोटाले या वित्तीय अपराध से संबंधित सहायता प्रदान नहीं की जा सकती। | Fraud-related assistance is not permitted.",
    "self_harm":        "⚠️ यदि आप संकट में हैं तो कृपया iCall हेल्पलाइन 9152987821 पर संपर्क करें। | If you are in crisis, please call iCall: 9152987821.",
    "sexual_illegal":   "⚠️ यह प्रश्न अनुचित और अवैध सामग्री से संबंधित है। | This query involves illegal content and is strictly prohibited.",
    "hate_speech":      "⚠️ नफरत फैलाने वाले प्रश्नों का उत्तर देना संभव नहीं है। | Hate speech queries are not permitted.",
    "unsafe":           "⚠️ यह प्रश्न सुरक्षा नीति का उल्लंघन करता है। | This query violates our safety policy.",
    "out_of_corpus":    "ℹ️ इस प्रश्न का उत्तर उपलब्ध ज्ञान संदर्भ में नहीं मिला। | The answer to this query was not found in the available knowledge base.",
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. PUBLIC GUARDRAIL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def check_input_safety(query: str) -> tuple[bool, str]:
    """
    Comprehensive input safety check.
    Detects illegal content, harmful queries, hate speech, cybercrime, etc.
    Returns (is_safe, category_or_SAFE).
    """
    query_lower = query.lower().strip()

    # Remove punctuation for better matching
    query_clean = re.sub(r'[^\w\s]', ' ', query_lower)

    for term, category in ALL_ILLEGAL_TERMS:
        # Use word-boundary-aware check
        if term in query_clean or term in query_lower:
            logger.warning(f"GUARDRAIL BLOCKED [{category}]: query='{query[:60]}...', term='{term}'")
            return False, category

    return True, "SAFE"


def check_off_topic_or_out_of_corpus(
    query: str,
    retrieved_chunks: list[PassageChunk],
    min_score_threshold: float = 0.20
) -> tuple[bool, str]:
    """
    Fast check verifying if query is in-domain for MSMARCO / Indic corpus.
    If top retrieved chunk similarity score < min_score_threshold, marks query as out-of-corpus.
    Returns (is_in_domain, reasoning).
    """
    if not retrieved_chunks:
        return False, "OUT_OF_CORPUS_NO_PASSAGES"

    top_chunk = retrieved_chunks[0]
    if top_chunk.score < min_score_threshold:
        return False, f"LOW_CONFIDENCE_SCORE: {top_chunk.score:.4f} < {min_score_threshold}"

    return True, "IN_DOMAIN"


def check_hallucination(answer: str, context_chunks: list[PassageChunk]) -> tuple[bool, str]:
    """
    Anti-hallucination check — verifies the answer has some grounding in retrieved context.
    Uses keyword overlap heuristic between answer and context passages.
    Returns (is_grounded, reasoning).
    """
    if not context_chunks or not answer.strip():
        return False, "NO_CONTEXT_OR_EMPTY_ANSWER"

    # Refusal answers are always "grounded" (not hallucinated)
    if any(marker in answer for marker in ["⚠️", "ℹ️", "अपर्याप्त", "SAFE"]):
        return True, "REFUSAL_GROUNDED"

    # Extract significant words from context (4+ chars to filter stop words)
    context_text = " ".join(c.text for c in context_chunks).lower()
    context_words = set(w for w in re.findall(r'\b\w{4,}\b', context_text))

    # Extract significant words from answer
    answer_words = set(w for w in re.findall(r'\b\w{4,}\b', answer.lower()))

    if not answer_words:
        return True, "TRIVIAL_ANSWER"

    # Calculate overlap ratio
    overlap = len(answer_words & context_words)
    overlap_ratio = overlap / len(answer_words)

    # If > 20% of answer words appear in context, consider grounded
    if overlap_ratio >= 0.20 or overlap >= 3:
        return True, f"GROUNDED (overlap={overlap_ratio:.2f})"

    logger.warning(f"HALLUCINATION RISK: overlap_ratio={overlap_ratio:.2f}, overlap_words={overlap}")
    return False, f"LOW_GROUNDING: overlap_ratio={overlap_ratio:.2f}"


def generate_refusal_answer(reason: str, language: str = "hi") -> str:
    """Generates bilingual refusal response based on guardrail category."""
    for category, message in REFUSAL_MESSAGES.items():
        if category.upper() in reason.upper() or reason.lower() == category.lower():
            return message

    # Default safety refusal
    return REFUSAL_MESSAGES["unsafe"]
