"""Deterministic reorder suggestions — no LLM, just math.

    daily_rate[p]  = units sold last N days / N
    days_left[p]   = stock / daily_rate          (inf if rate == 0)
    reorder if     days_left < lead_time + safety_days
    suggested_qty  = ceil((rate*(lead+safety) - stock) / pack_size)*pack_size

Sorted by urgency (days_left ascending).
"""

from __future__ import annotations

import math

from bolta.ledger import Ledger

LEAD_TIME_DAYS = 2      # supplier delivers in ~2 days
SAFETY_DAYS = 3         # buffer stock


def suggestions(db: Ledger, *, days: int = 14,
                lead_time: int = LEAD_TIME_DAYS,
                safety_days: int = SAFETY_DAYS,
                limit: int = 20) -> list[dict]:
    out = []
    horizon = lead_time + safety_days
    for p in db.products():
        rate = db.sales_history(p["id"], days) / days
        stock = float(p["stock"])
        days_left = stock / rate if rate > 0 else math.inf
        if days_left >= horizon:
            continue
        need = rate * horizon - stock
        pack = max(1, int(p["pack_size"]))
        qty = max(pack, math.ceil(need / pack) * pack)
        out.append({
            "product_id": p["id"], "name_en": p["name_en"],
            "stock": stock, "daily_rate": round(rate, 2),
            "days_left": round(days_left, 1), "qty": qty,
            "unit": p["unit"],
        })
    out.sort(key=lambda x: x["days_left"])
    return out[:limit]
