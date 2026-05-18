"""
Webhook Service — receives Odoo 19 native and custom webhook payloads.
Auto-detects format and updates local catalog.
"""

import hmac
import hashlib
from datetime import datetime
from typing import List

from config import supabase_client, WEBHOOK_SECRET, SYNC_LOG_TABLE
from services import odoo, catalog


def verify_signature(payload_bytes: bytes, signature: str) -> bool:
    if not WEBHOOK_SECRET:
        return True
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


def log_sync_event(source: str, event_type: str, product_ids: List[int], status: str, detail: str = ""):
    try:
        supabase_client.table(SYNC_LOG_TABLE).insert({
            "source": source, "event_type": event_type, "product_ids": product_ids,
            "status": status, "detail": detail, "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception as e:
        print(f"[SYNC LOG] Failed: {type(e).__name__}: {e}")


def _is_native(event: dict) -> bool:
    return "_id" in event and "_model" in event


def _handle_native(event: dict) -> dict:
    model = event.get("_model", "")
    record_id = event.get("_id")
    print(f"[WEBHOOK] Odoo 19 native: model={model}, id={record_id}")

    if not record_id:
        return {"status": "skipped", "reason": "no _id"}

    product_ids = []
    if model == "product.template":
        product_ids = [record_id]
    elif model == "stock.move":
        try:
            moves = odoo.execute("stock.move", "read", [record_id], fields=["product_id"])
            if moves:
                prod = moves[0].get("product_id")
                if prod:
                    prod_id = prod[0] if isinstance(prod, (list, tuple)) else prod
                    products = odoo.execute("product.product", "read", [prod_id], fields=["product_tmpl_id"])
                    if products:
                        tmpl = products[0].get("product_tmpl_id")
                        product_ids = [tmpl[0] if isinstance(tmpl, (list, tuple)) else tmpl]
        except Exception as e:
            log_sync_event("webhook", "stock.move.error", [record_id], "error", str(e))
            return {"status": "error", "reason": str(e)}
    else:
        return {"status": "skipped", "reason": f"unhandled model: {model}"}

    if not product_ids:
        return {"status": "skipped", "reason": "could not resolve product_ids"}

    odoo_products = odoo.fetch_by_ids(product_ids)
    if not odoo_products:
        log_sync_event("webhook", f"{model}.sync", product_ids, "warn", "no data from Odoo")
        return {"status": "warn", "reason": "could not fetch from Odoo"}

    local_rows = [odoo.to_local_row(p) for p in odoo_products]
    result = catalog.upsert(local_rows)
    log_sync_event("webhook", f"{model}.sync", product_ids, "ok", f"upserted {result['upserted']}")
    print(f"[WEBHOOK] Synced {product_ids}: upserted {result['upserted']}")
    return {"status": "ok", **result}


def _handle_custom(event: dict) -> dict:
    event_type = event.get("event", "unknown")
    product_ids = event.get("product_ids", [])
    if not product_ids:
        return {"status": "skipped", "reason": "no product_ids"}

    if event_type == "product.unlink":
        count = catalog.deactivate(product_ids)
        log_sync_event("webhook", event_type, product_ids, "ok", f"deactivated {count}")
        return {"status": "ok", "deactivated": count}

    odoo_products = odoo.fetch_by_ids(product_ids)
    if not odoo_products:
        log_sync_event("webhook", event_type, product_ids, "warn", "no data from Odoo")
        return {"status": "warn", "reason": "could not fetch from Odoo"}

    local_rows = [odoo.to_local_row(p) for p in odoo_products]
    result = catalog.upsert(local_rows)
    log_sync_event("webhook", event_type, product_ids, "ok", f"upserted {result['upserted']}")
    return {"status": "ok", **result}


def handle_event(event: dict) -> dict:
    return _handle_native(event) if _is_native(event) else _handle_custom(event)
