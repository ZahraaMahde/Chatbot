"""
Axion Assistant API — FastAPI routes only.
All business logic lives in services/ and orchestrator.py.
"""

import os
import json
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from config import (
    openai_client, SYNC_API_KEY, OPENAI_API_KEY, SUPABASE_URL,
    LOCAL_CATALOG_TABLE, TRANSCRIBE_MODEL, supabase_client, SYNC_LOG_TABLE,
)
from utils import normalize_whitespace, parse_latency_to_seconds
from services import odoo, chat, catalog, webhook
from services.reconcile import full_sync
from services.rag import extract_source_pages
import orchestrator


# ── App Setup ──
app = FastAPI(title="Axion Assistant API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")


# ── Request Models ──
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class CatalogUpsertItem(BaseModel):
    product_id: int
    name: str
    default_code: Optional[str] = ""
    category_name: Optional[str] = ""
    category_id: Optional[int] = None
    description: Optional[str] = ""
    brand: Optional[str] = ""
    search_text: Optional[str] = ""
    active: Optional[bool] = True
    image_url: Optional[str] = ""
    last_synced_at: Optional[str] = None


class CatalogUpsertRequest(BaseModel):
    items: List[CatalogUpsertItem]


# ── Routes ──
@app.get("/")
def serve_index():
    index_path = frontend_dir / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return JSONResponse({"error": "frontend/index.html not found"}, status_code=500)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "odoo_connected": odoo.is_connected(),
        "supabase_url_present": bool(SUPABASE_URL),
        "openai_present": bool(OPENAI_API_KEY),
        "catalog_table": LOCAL_CATALOG_TABLE,
        "sync_mode": "webhook + nightly reconcile",
    }


@app.post("/api/chat")
def chat_api(req: ChatRequest):
    message = normalize_whitespace(req.message)
    if not message:
        return JSONResponse({"error": "Empty message"}, status_code=400)

    session_id = req.session_id or chat.create_session()
    chat.save_message(session_id, "user", message)

    answer, latency, hits = orchestrator.answer(message, session_id=session_id)

    latency_s = parse_latency_to_seconds(latency)
    chat.save_message(session_id, "assistant", answer, latency_s)

    return {
        "session_id": session_id,
        "answer": answer,
        "latency": latency,
        "sources_pages": extract_source_pages(hits),
    }


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    suffix = Path(audio.filename or "voice.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await audio.read())
        temp_path = tmp.name
    try:
        with open(temp_path, "rb") as f:
            resp = openai_client.audio.transcriptions.create(model=TRANSCRIBE_MODEL, file=f)
        return {"transcript": resp.text or ""}
    except Exception as e:
        return JSONResponse({"error": f"Transcription failed: {type(e).__name__}: {e}"}, status_code=500)
    finally:
        try:
            os.remove(temp_path)
        except Exception:
            pass


@app.post("/api/webhook/odoo")
async def webhook_odoo(request: Request):
    body = await request.body()
    print(f"[WEBHOOK] Received: {body[:500]}")

    signature = request.headers.get("X-Webhook-Signature", "")
    if not webhook.verify_signature(body, signature):
        webhook.log_sync_event("webhook", "auth_fail", [], "error", "invalid signature")
        return JSONResponse({"error": "Invalid signature"}, status_code=401)

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)

    return webhook.handle_event(event)


@app.post("/api/sync/reconcile")
def sync_reconcile(x_sync_key: Optional[str] = Header(default=None)):
    if SYNC_API_KEY and x_sync_key != SYNC_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    return full_sync()


@app.post("/api/catalog/upsert")
def catalog_upsert_api(req: CatalogUpsertRequest, x_sync_key: Optional[str] = Header(default=None)):
    if SYNC_API_KEY and x_sync_key != SYNC_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    rows = []
    for item in req.items:
        rows.append({
            "product_id": item.product_id, "name": item.name,
            "default_code": item.default_code or "", "category_name": item.category_name or "",
            "category_id": item.category_id, "description": item.description or "",
            "brand": item.brand or "",
            "search_text": item.search_text or " ".join(filter(None, [item.name, item.default_code, item.category_name, item.brand, item.description])),
            "active": True if item.active is None else item.active,
            "image_url": item.image_url or "",
            "last_synced_at": item.last_synced_at or datetime.utcnow().isoformat(),
        })
    try:
        return catalog.upsert(rows)
    except RuntimeError as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/sync/status")
def sync_status(x_sync_key: Optional[str] = Header(default=None)):
    if SYNC_API_KEY and x_sync_key != SYNC_API_KEY:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    try:
        resp = supabase_client.table(SYNC_LOG_TABLE).select("*").order("created_at", desc=True).limit(20).execute()
        return {"recent_events": resp.data or []}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
