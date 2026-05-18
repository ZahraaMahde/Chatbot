"""
RAG Service — embedding-based document retrieval from Supabase.
"""

from typing import List
from config import supabase_client, embeddings_client


def retrieve_chunks(question: str, k: int = 4) -> List[dict]:
    try:
        q_vec = embeddings_client.embed_query(question)
        resp = supabase_client.rpc("match_rag_chunks", {"query_embedding": q_vec, "match_count": k}).execute()
        return resp.data or []
    except Exception as e:
        print(f"rag.retrieve_chunks error: {type(e).__name__}: {e}")
        return []


def build_context(chunks: List[dict], k: int = 4) -> str:
    if not chunks:
        return "(none)"
    return "\n\n".join(f"[p{c.get('page', '?')}] {c.get('content', '')}" for c in chunks[:k])


def extract_source_pages(chunks: List[dict]) -> List[int]:
    pages = set()
    for c in chunks:
        p = c.get("page")
        if p is not None:
            pages.add(p + 1)
    return sorted(pages)
