"""
Odoo Sync Service — JSON-RPC connection for sync operations ONLY.
NEVER called during a user chat conversation.
"""

import time
from datetime import datetime
from typing import Any, List, Optional

import requests

from config import ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD


_uid: Optional[int] = None
_session: Optional[requests.Session] = None
_rpc_url: str = ""
_rpc_id: int = 0

PRODUCT_FIELDS = [
    "id", "name", "default_code", "list_price",
    "qty_available", "virtual_available", "categ_id",
    "active", "write_date",
]


def _jsonrpc(endpoint: str, method: str, *args) -> Any:
    global _rpc_id
    if _session is None:
        raise RuntimeError("Odoo session not initialized")
    _rpc_id += 1
    payload = {
        "jsonrpc": "2.0", "method": "call", "id": _rpc_id,
        "params": {"service": endpoint, "method": method, "args": list(args)},
    }
    resp = _session.post(_rpc_url, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"Odoo RPC error: {data['error']}")
    return data["result"]


def execute(model: str, method: str, domain, **kwargs) -> Any:
    return _jsonrpc("object", "execute_kw", ODOO_DB, _uid, ODOO_PASSWORD, model, method, [domain], kwargs)


def connect():
    global _uid, _session, _rpc_url
    if not all([ODOO_URL, ODOO_DB, ODOO_USER, ODOO_PASSWORD]):
        print("[SYNC] Odoo credentials missing. Sync disabled.")
        return
    try:
        _rpc_url = f"{ODOO_URL}/jsonrpc"
        _session = requests.Session()
        _session.headers.update({"Content-Type": "application/json", "Accept": "application/json"})
        _uid = _jsonrpc("common", "authenticate", ODOO_DB, ODOO_USER, ODOO_PASSWORD, {})
        print(f"[SYNC] Connected to Odoo as uid={_uid}")
    except Exception as e:
        print(f"[SYNC] Odoo connection failed: {type(e).__name__}: {e}")
        _uid = None
        _session = None


def is_connected() -> bool:
    return _uid is not None


def fetch_by_ids(product_ids: List[int]) -> List[dict]:
    if not is_connected() or not product_ids:
        return []
    try:
        return execute("product.template", "read", product_ids, fields=PRODUCT_FIELDS)
    except Exception as e:
        print(f"[SYNC] fetch_by_ids error: {type(e).__name__}: {e}")
        return []


def fetch_all(limit: int = 5000) -> List[dict]:
    if not is_connected():
        return []
    try:
        t0 = time.perf_counter()
        rows = execute("product.template", "search_read", [["active", "in", [True, False]]], fields=PRODUCT_FIELDS, limit=limit)
        print(f"[RECONCILE] Fetched {len(rows)} products in {time.perf_counter() - t0:.2f}s")
        return rows
    except Exception as e:
        print(f"[RECONCILE] fetch_all error: {type(e).__name__}: {e}")
        return []


def to_local_row(p: dict) -> dict:
    return {
        "product_id": p.get("id"),
        "name": p.get("name", ""),
        "default_code": p.get("default_code", "") or "",
        "category_name": (p.get("categ_id") or [False, ""])[1],
        "category_id": (p.get("categ_id") or [False])[0] or None,
        "sales_price": p.get("list_price", 0),
        "quantity_on_hand": p.get("qty_available", 0),
        "forecasted_quantity": p.get("virtual_available", 0),
        "in_stock": (p.get("qty_available", 0) or 0) > 0,
        "active": p.get("active", True),
        "search_text": " ".join(filter(None, [
            p.get("name", ""), p.get("default_code", ""),
            (p.get("categ_id") or [False, ""])[1],
        ])),
        "last_synced_at": datetime.utcnow().isoformat(),
        "sync_source": "odoo",
    }


# Connect on import
connect()
