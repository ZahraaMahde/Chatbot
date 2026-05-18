"""
Pure utility functions — no side effects, no API calls, no state.
"""

import re
from datetime import datetime
from typing import Optional

from config import LEBANON_TZ


def detect_lang(text: str) -> str:
    if re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", text or ""):
        return "ar"
    return "en"


def now_in_lebanon() -> datetime:
    return datetime.now(LEBANON_TZ)


def format_now(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " (Asia/Beirut)"


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


TERM_NORMALIZATION = {
    "screenas": "screens", "screenes": "screens",
    "screns": "screens", "screans": "screens",
    "moniters": "monitors", "minitors": "monitors",
    "moniter": "monitor",
    "camras": "cameras", "camra": "camera",
    "routrs": "routers", "swiches": "switches",
}

GENERIC_ALIASES = {
    "screens": "monitor", "screen": "monitor",
    "displays": "monitor", "display": "monitor",
}


def normalize_terms(text: str) -> str:
    words = normalize_whitespace(text).lower().split()
    return " ".join(GENERIC_ALIASES.get(TERM_NORMALIZATION.get(w, w), TERM_NORMALIZATION.get(w, w)) for w in words)


def extract_search_phrase(question: str) -> str:
    q = normalize_whitespace(question).lower()

    for p in [
        r"^go to stock and tell me all\s+", r"^go to stock and tell me\s+",
        r"^tell me all\s+", r"^show me all\s+", r"^show me\s+", r"^tell me\s+",
        r"^list all\s+", r"^list\s+", r"^do you have\s+", r"^what do you have\s+",
        r"^i want\s+", r"^i need\s+", r"^find\s+", r"^search for\s+", r"^search\s+",
    ]:
        q = re.sub(p, "", q, flags=re.I)

    for p in [
        r"\byou have\b", r"\bin stock\b", r"\bavailable\b", r"\bavailability\b",
        r"\bproducts\b", r"\bproduct\b", r"\bplease\b", r"\bfor me\b", r"\bgo to stock\b",
    ]:
        q = re.sub(p, " ", q, flags=re.I)

    q = re.sub(r"[^\w\s/\-]", " ", q)
    q = re.sub(r"\s+", " ", q).strip()
    q = normalize_terms(q)
    return q or normalize_terms(normalize_whitespace(question))


def parse_latency_to_seconds(latency_str: str) -> Optional[float]:
    try:
        match = re.match(r"^\s*([0-9]*\.?[0-9]+)s", latency_str or "")
        return round(float(match.group(1)), 3) if match else None
    except Exception:
        return None
