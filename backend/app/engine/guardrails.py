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
    "weapons": [
        "bomb", "bombs", "bombing", "make a bomb", "making a bomb", "how to make a bomb",
        "bomb process", "bomb making", "explosive", "explosives", "improvised explosive",
        "बॉम्ब", "बॉम", "बम", "बम्ब", "बॉम्ब्स", "बॉम्ब बनाने", "बम बनाने", "बनाया जाता है",
        "विस्फोटक", "विस्फोट", "धमाका", "chemical weapon", "biological weapon",
        "weapon", "weapons", "gun", "pistol", "rifle", "grenade", "ak47", "ak-47",
        "हथियार", "हथियारों", "बंदूक", "पिस्तौल", "गोली", "राइफल", "तपंचा", "कट्टा"
    ],
    "violence": [
        "blast", "kill", "murder", "मारना", "हत्या", "shoot", "knife attack", "चाकू",
        "terrorism", "आतंकवाद", "terrorist", "jihad", "genocide", "नरसंहार",
        "mass shooting", "beheading", "गर्दन काटना"
    ],
    "drugs": [
        "heroin", "cocaine", "meth", "crystal meth", "drugs kaise", "नशा कैसे",
        "drug trafficking", "smuggling", "तस्करी", "mdma", "lsd", "ketamine",
        "how to make drugs", "ड्रग्स कैसे बनाएं", "नशा", "नशीले", "गांजा", "चरस", "अफीम"
    ],
    "cybercrime": [
        "hack", "hacking", "hacker", "malware", "ransomware", "phishing", "ddos", "exploit",
        "sql injection", "crack password", "पासवर्ड तोड़ना", "keylogger", "trojan",
        "bypass security", "how to hack", "हैकिंग", "हैक"
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
# 2. REFUSAL MESSAGES (Language-Aware Safety Notices)
# ─────────────────────────────────────────────────────────────────────────────

REFUSAL_MESSAGES = {
    "en": "⚠️ Safety Notice: Queries regarding explosives, weapons, or illegal activities are strictly prohibited.",
    "hi": "⚠️ सुरक्षा सूचना: बम, हथियार निर्माण, हिंसा या अवैध गतिविधियों से संबंधित प्रश्नों का उत्तर देना सख्त मना है।",
    "mr": "⚠️ सुरक्षा सूचना: बॉम्ब, शस्त्र निर्मिती किंवा बेकायदेशीर गोष्टींबाबत माहिती देणे पूर्णपणे प्रतिबंधित आहे.",
    "bn": "⚠️ সুরক্ষা সতর্কতা: বোমা বা অস্ত্র তৈরি সংক্রান্ত প্রশ্নের উত্তর দেওয়া সম্পূর্ণ নিষিদ্ধ।",
    "ta": "⚠️ பாதுகாப்பு அறிவிப்பு: வெடிபொருட்கள் அல்லது சட்டவிரோத விஷயங்கள் குறித்த தகவல்கள் அனுமதிக்கப்படாது.",
    "te": "⚠️ భద్రతా సూచన: పేలుడు పదార్థాలు లేదా ఆయుధాల తయారీకి సంబంధించిన ప్రశ్నలు నిషేధించబడ్డాయి."
}


# ─────────────────────────────────────────────────────────────────────────────
# 3. PUBLIC GUARDRAIL FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

def check_input_safety(query: str) -> tuple[bool, str]:
    """
    Comprehensive input safety check.
    Detects illegal content, harmful queries, hate speech, cybercrime, explosives, etc.
    Returns (is_safe, category_or_SAFE).
    """
    query_lower = query.lower().strip()

    # Remove punctuation for better matching
    query_clean = re.sub(r'[^\w\s]', ' ', query_lower)

    for term, category in ALL_ILLEGAL_TERMS:
        # Check both cleaned text and direct substring match (crucial for Devanagari diacritics like बॉम्ब)
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
    if any(marker in answer for marker in ["⚠️", "ℹ️", "सुरक्षा", "Notice", "अपर्याप्त", "SAFE"]):
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
    """Generates language-aware safety refusal response based on guardrail category."""
    lang_key = (language or "hi").split("-")[0].lower()
    if lang_key in REFUSAL_MESSAGES:
        return REFUSAL_MESSAGES[lang_key]
    return REFUSAL_MESSAGES["hi"]
