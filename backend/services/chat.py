"""
Chat Service — session creation, message persistence, history retrieval.
"""

from typing import List, Optional
from config import supabase_client, LATENCY_COLUMN


def create_session(title: Optional[str] = None) -> Optional[str]:
    try:
        resp = supabase_client.table("chat_sessions").insert({"title": title or "Axion Assistant Chat"}).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception as e:
        print(f"chat.create_session error: {type(e).__name__}: {e}")
        return None


def save_message(session_id: Optional[str], role: str, content: str, latency_s: Optional[float] = None):
    if not session_id:
        return None
    payload = {"session_id": session_id, "role": role, "content": content}
    if latency_s is not None:
        payload[LATENCY_COLUMN] = latency_s
    try:
        return supabase_client.table("chat_messages").insert(payload).execute()
    except Exception as e:
        print(f"chat.save_message error: {type(e).__name__}: {e}")
        return None


def fetch_history(session_id: Optional[str], last_n: int = 10) -> List[dict]:
    """Fetch last N messages for conversation context, oldest first."""
    if not session_id:
        return []
    try:
        resp = (
            supabase_client.table("chat_messages")
            .select("role,content")
            .eq("session_id", session_id)
            .order("created_at", desc=True)
            .limit(last_n)
            .execute()
        )
        rows = resp.data or []
        rows.reverse()
        return [{"role": r["role"], "content": r["content"]} for r in rows]
    except Exception as e:
        print(f"chat.fetch_history error: {type(e).__name__}: {e}")
        return []
