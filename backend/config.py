"""
Centralized configuration: env vars, API clients, constants.
Every other module imports from here — never reads os.environ directly.
"""

import os
from zoneinfo import ZoneInfo

from openai import OpenAI
from supabase import create_client
from langchain_openai import OpenAIEmbeddings


def _env(key: str) -> str:
    return (os.getenv(key) or "").strip()


# ── API Keys & URLs ──
OPENAI_API_KEY   = _env("OPENAI_API_KEY")
SUPABASE_URL     = _env("SUPABASE_URL")
SUPABASE_KEY     = _env("SUPABASE_KEY")
ODOO_URL         = _env("ODOO_URL")
ODOO_DB          = _env("ODOO_DB")
ODOO_USER        = _env("ODOO_USER")
ODOO_PASSWORD    = _env("ODOO_PASSWORD")
SYNC_API_KEY     = _env("SYNC_API_KEY")
WEBHOOK_SECRET   = _env("WEBHOOK_SECRET")
KAFKA_BROKER     = _env("KAFKA_BROKER")
KAFKA_TOPIC      = _env("KAFKA_TOPIC")
KAFKA_GROUP_ID   = _env("KAFKA_GROUP_ID")

# ── Model & Table Constants ──
EMBED_MODEL          = "text-embedding-3-small"
LLM_MODEL            = "gpt-4o-mini"
TRANSCRIBE_MODEL     = "gpt-4o-mini-transcribe"
LOCAL_CATALOG_TABLE  = "catalog_products"
SYNC_LOG_TABLE       = "sync_log"
LATENCY_COLUMN       = "latency_s"
LEBANON_TZ           = ZoneInfo("Asia/Beirut")

# ── Guard Required Keys ──
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set.")
if not SUPABASE_URL:
    raise RuntimeError("SUPABASE_URL is not set.")
if not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_KEY is not set.")

# ── Shared Clients ──
openai_client     = OpenAI(api_key=OPENAI_API_KEY)
supabase_client   = create_client(SUPABASE_URL, SUPABASE_KEY)
embeddings_client = OpenAIEmbeddings(model=EMBED_MODEL, api_key=OPENAI_API_KEY)
