"""
Catalog Service — local-only product search and management.
The chatbot queries ONLY this. No Odoo calls happen here.
"""

import time
from datetime import datetime
from typing import List, Dict

from config import supabase_client, LOCAL_CATALOG_TABLE
from utils import extract_search_phrase, normalize_whitespace


_FILLER_WORDS = {
    "the", "and", "for", "that", "this", "with", "from", "can",
    "you", "have", "what", "how", "want", "need", "wanna", "gonna",
    "some", "any", "all", "but", "not", "are", "was", "were",
    "been", "being", "has", "had", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "must",
    "very", "really", "just", "also", "too", "much", "many",
    "home", "work", "setup", "remotly", "remolty", "remotely",
    "make", "like", "look", "tell", "show", "give", "get",
    "iam", "hmmm", "hmm", "umm", "hey", "please",
    "suggest", "recommend", "best", "good",
}


def _extract_keywords(query: str) -> List[str]:
    phrase = extract_search_phrase(query)
    words = phrase.split()
    keywords = [w for w in words if len(w) >= 3 and w not in _FILLER_WORDS]
    return keywords if keywords else words[:3]


def search(query: str, limit: int = 10) -> List[dict]:
    """Search local catalog. FTS first, ilike fallback."""
    keywords = _extract_keywords(query)
    search_phrase = " ".join(keywords) if keywords else extract_search_phrase(query)
    if not search_phrase:
        return []

    # Strategy 1: Full-text search RPC
    try:
        t0 = time.perf_counter()
        resp = supabase_client.rpc("search_catalog", {"search_query": search_phrase, "max_results": limit}).execute()
        rows = resp.data or []
        print(f"catalog.search (FTS) '{search_phrase}' → {len(rows)} rows in {time.perf_counter() - t0:.3f}s")
        if rows:
            return rows[:limit]
    except Exception as e:
        print(f"catalog.search FTS error: {type(e).__name__}: {e}")

    # Strategy 2: ilike fallback per keyword
    all_rows, seen_ids = [], set()
    for kw in keywords[:3]:
        try:
            t0 = time.perf_counter()
            resp = (
                supabase_client.table(LOCAL_CATALOG_TABLE)
                .select("product_id,name,default_code,category_name,category_id,sales_price,quantity_on_hand,forecasted_quantity,in_stock,active")
                .or_(f"name.ilike.%{kw}%,category_name.ilike.%{kw}%,search_text.ilike.%{kw}%")
                .eq("active", True).limit(limit).execute()
            )
            print(f"catalog.search (ilike) '{kw}' → {len(resp.data or [])} rows in {time.perf_counter() - t0:.3f}s")
            for row in (resp.data or []):
                pid = row.get("product_id")
                if pid not in seen_ids:
                    seen_ids.add(pid)
                    all_rows.append(row)
        except Exception as e:
            print(f"catalog.search ilike error for '{kw}': {type(e).__name__}: {e}")
        if len(all_rows) >= limit:
            break
    return all_rows[:limit]


def upsert(rows: List[dict]) -> dict:
    if not rows:
        return {"upserted": 0, "data_count": 0}
    try:
        resp = supabase_client.table(LOCAL_CATALOG_TABLE).upsert(rows, on_conflict="product_id").execute()
        return {"upserted": len(rows), "data_count": len(resp.data or [])}
    except Exception as e:
        raise RuntimeError(f"Catalog upsert failed: {type(e).__name__}: {e}")


def deactivate(product_ids: List[int]) -> int:
    if not product_ids:
        return 0
    try:
        resp = (supabase_client.table(LOCAL_CATALOG_TABLE)
                .update({"active": False, "in_stock": False, "last_synced_at": datetime.utcnow().isoformat()})
                .in_("product_id", product_ids).execute())
        return len(resp.data or [])
    except Exception as e:
        print(f"catalog.deactivate error: {type(e).__name__}: {e}")
        return 0


def get_all_ids() -> set:
    try:
        resp = supabase_client.table(LOCAL_CATALOG_TABLE).select("product_id").execute()
        return {r["product_id"] for r in (resp.data or [])}
    except Exception as e:
        print(f"catalog.get_all_ids error: {type(e).__name__}: {e}")
        return set()
