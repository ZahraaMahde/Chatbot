"""
Reconcile Service — nightly full diff between Odoo and local catalog.
"""

import time
from services import odoo, catalog
from services.webhook import log_sync_event


def full_sync() -> dict:
    t0 = time.perf_counter()
    odoo_products = odoo.fetch_all()
    if not odoo_products:
        log_sync_event("reconcile", "full_sync", [], "warn", "no products from Odoo")
        return {"status": "warn", "reason": "no products from Odoo"}

    local_rows = [odoo.to_local_row(p) for p in odoo_products]
    result = catalog.upsert(local_rows)

    odoo_ids = {p["id"] for p in odoo_products}
    local_ids = catalog.get_all_ids()
    orphaned = list(local_ids - odoo_ids)
    deactivated = catalog.deactivate(orphaned) if orphaned else 0

    elapsed = time.perf_counter() - t0
    summary = f"synced {result['upserted']}, deactivated {deactivated} in {elapsed:.2f}s"
    log_sync_event("reconcile", "full_sync", [], "ok", summary)
    print(f"[RECONCILE] {summary}")

    return {"status": "ok", "synced": result["upserted"], "deactivated": deactivated, "elapsed_s": round(elapsed, 2)}
