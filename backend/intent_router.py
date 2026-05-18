"""
Intent Router — classifies every message BEFORE any service runs.
Returns: {"intent": "smalltalk" | "inventory" | "rag_only"}
"""

import re
from utils import normalize_whitespace, normalize_terms


_SMALLTALK_PHRASES = {
    "hi", "hello", "hey", "yo", "sup",
    "thanks", "thank you", "thx", "ty",
    "ok", "okay", "sure", "alright",
    "wow", "nice", "cool", "great", "awesome", "amazing",
    "yes", "no", "yep", "nope", "yeah", "nah",
    "bye", "goodbye", "see you", "good night",
    "good morning", "good afternoon", "good evening",
    "how are you", "what's up", "whats up",
    "who are you", "what are you", "what can you do",
    "مرحبا", "هلا", "السلام عليكم", "شكرا", "شكرًا",
    "أهلا", "أهلاً", "مرحباً", "صباح الخير", "مساء الخير",
    "كيف حالك", "كيفك", "تمام", "حسنا", "نعم", "لا",
    "مع السلامة", "باي", "يعطيك العافية",
}

_CONVERSATIONAL_WORDS = {
    "wow", "nice", "cool", "great", "awesome", "amazing", "perfect",
    "ok", "okay", "sure", "alright", "yes", "no", "yep", "nope",
    "thanks", "thank", "please", "sorry", "help", "what", "how",
    "why", "when", "where", "who", "can", "could", "would", "should",
    "will", "do", "does", "did", "is", "are", "was", "were",
    "the", "a", "an", "this", "that", "it", "i", "you", "we", "they",
    "my", "your", "me", "him", "her", "us", "them",
    "not", "but", "and", "or", "if", "so", "too", "also",
    "very", "really", "just", "more", "much", "many",
    "good", "bad", "need", "want", "like", "know", "think",
    "tell", "show", "give", "get", "make", "go", "come",
}

_KNOWN_PRODUCT_HINTS = {
    "lg", "samsung", "dell", "hp", "lenovo", "asus", "acer", "ubiquiti",
    "monitor", "monitors", "screen", "screens", "display", "displays",
    "router", "routers", "switch", "switches", "camera", "cameras",
    "laptop", "laptops", "server", "servers", "phone", "phones",
    "cable", "cables", "fiber", "patch", "panel", "access", "point",
    "antenna", "battery", "adapter", "connector", "rack", "ups",
    "network", "ethernet", "wireless", "wifi", "wi-fi",
}

_INVENTORY_PATTERN = re.compile(
    r"\b(stock|inventory|available|in stock|quantity|qty|price|cost|product|products|"
    r"category|categories|do you have|what do you have|setup|install)\b", re.I,
)

_STOCK_CHECK_PATTERN = re.compile(
    r"\b(in stock|available|availability|how many|quantity|qty|stock of|stock for)\b", re.I,
)


def is_smalltalk(question: str) -> bool:
    return normalize_whitespace(question).lower() in _SMALLTALK_PHRASES


def _is_inventory_request(q: str) -> bool:
    if _INVENTORY_PATTERN.search(q):
        return True
    words = set(re.findall(r"\b[\w\-]+\b", q))
    if words & _KNOWN_PRODUCT_HINTS:
        return True
    if len(words) <= 2:
        non_conv = words - _CONVERSATIONAL_WORDS
        return bool(non_conv and (non_conv & _KNOWN_PRODUCT_HINTS))
    return False


def classify(question: str) -> dict:
    q = normalize_terms(normalize_whitespace(question).lower())
    if is_smalltalk(q):
        return {"intent": "smalltalk"}
    if _STOCK_CHECK_PATTERN.search(q):
        return {"intent": "inventory"}
    if _is_inventory_request(q):
        return {"intent": "inventory"}
    return {"intent": "rag_only"}
