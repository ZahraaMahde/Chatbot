"""
Orchestrator — coordinates intent router + services to produce an answer.
Optimized for low latency:
- Smalltalk returns instantly.
- Inventory/catalog queries return directly without LLM by default.
- RAG is only used for knowledge-base questions.
"""

import time
from typing import List, Optional, Tuple

from utils import detect_lang, normalize_whitespace
from intent_router import is_smalltalk, classify
from services import rag, llm, catalog, chat


def answer(question: str, session_id: Optional[str] = None, k: int = 3) -> Tuple[str, str, List[dict]]:
    start = time.perf_counter()

    lang = detect_lang(question)
    qnorm = normalize_whitespace(question).lower()

    # 1. Smalltalk: no database, no LLM.
    if is_smalltalk(qnorm):
        text = llm.format_smalltalk(lang)
        return text, f"{time.perf_counter() - start:.2f}s", []

    intent = classify(question)["intent"]

    # 2. Inventory/catalog: Supabase search only, no LLM.
    # This is the biggest latency improvement.
    if intent == "inventory":
        t_cat = time.perf_counter()
        products = catalog.search(question, limit=10)
        catalog_s = time.perf_counter() - t_cat

        text = llm.format_inventory_answer_fast(question, products, lang)

        total = time.perf_counter() - start
        return text, f"{total:.2f}s (Catalog {catalog_s:.3f}s | LLM 0.00s)", []

    # 3. RAG questions only.
    # Fetch history only for RAG, not for inventory.
    history = chat.fetch_history(session_id, last_n=6) if session_id else []

    t_rag = time.perf_counter()
    chunks = rag.retrieve_chunks(question, k=k)
    rag_s = time.perf_counter() - t_rag

    pdf_context = rag.build_context(chunks, k=k)

    t_llm = time.perf_counter()
    text = llm.generate_rag_answer(question, pdf_context, lang, history=history)
    llm_s = time.perf_counter() - t_llm

    source_pages = rag.extract_source_pages(chunks)
    text = llm.append_sources(text, source_pages, lang)

    total = time.perf_counter() - start
    return text, f"{total:.2f}s (RAG {rag_s:.2f}s | LLM {llm_s:.2f}s)", chunks
