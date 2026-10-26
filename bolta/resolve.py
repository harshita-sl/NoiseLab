"""Resolve slot mentions to DB rows via fuzzy matching.

Uses difflib ratio against every catalog alias (en + hi + alias list).
Two candidates within AMBIGUITY_DELTA of the winner -> ambiguity:
the confirm card asks, we never silent-pick.
"""

from __future__ import annotations

import difflib

from bolta.ledger import Ledger
from bolta.parse import Command
from noiselab.normalize import canonical, normalize_text

MATCH_THRESHOLD = 0.62   # below this: unresolved
AMBIGUITY_DELTA = 0.10   # within this of winner: ambiguous


def _aliases(row) -> list[str]:
    names = [row["name_en"] if "name_en" in row.keys() else row["name"]]
    if "name_hi" in row.keys() and row["name_hi"]:
        names.append(row["name_hi"])
    names += [a for a in (row["aliases"] or "").split(",") if a.strip()]
    return [normalize_text(n) for n in names]


def _match(text: str, rows) -> tuple[object | None, float, list]:
    """Best row, its score, and ties within AMBIGUITY_DELTA."""
    q = normalize_text(text)
    if not q:
        return None, 0.0, []
    scored = []
    for row in rows:
        best = max(
            (difflib.SequenceMatcher(None, q, a).ratio()
             for a in _aliases(row) if a), default=0.0)
        # containment bonus: "maggi" inside "maggi noodles"
        # (len>=4 guard — "pe" inside "pepsodent" is a false hit)
        for a in _aliases(row):
            if len(q) >= 4 and a and (q in a or a in q):
                best = max(best, 0.85)
        scored.append((best, row))
    scored.sort(key=lambda t: t[0], reverse=True)
    if not scored or scored[0][0] < MATCH_THRESHOLD:
        return None, scored[0][0] if scored else 0.0, [
            r for s, r in scored[:3]]
    winner, wscore = scored[0][1], scored[0][0]
    ties = [r for s, r in scored[1:] if wscore - s < AMBIGUITY_DELTA]
    return winner, wscore, ties


def resolve(cmd: Command, db: Ledger) -> Command:
    """Fill customer_id / product_id / amount on a Command in place."""
    if cmd.slots.get("customer"):
        row, score, ties = _match(cmd.slots["customer"], db.customers())
        if cmd.intent == "add_customer":
            # name is NEW by definition — an existing match is info, not
            # a failure: proposal explains instead of duplicating
            if row is not None:
                cmd.slots["existing_id"] = row["id"]
                cmd.slots["customer_name"] = row["name"]
                cmd.slots["existing_balance"] = db.balance_paise(row["id"])
            else:
                cmd.slots["new_name"] = cmd.slots["customer"]
            cmd.slots.pop("customer", None)
        elif row is not None:
            cmd.slots["customer_id"] = row["id"]
            cmd.slots["customer_name"] = row["name"]
            if ties:
                cmd.slots["ambiguous_customer"] = [
                    t["name"] for t in [row] + ties]
                cmd.confidence = min(cmd.confidence, 0.55)
        else:
            cmd.unresolved.append("customer")
            cmd.slots["near_customer"] = [
                r["name"] for r in ties]  # ties holds top-3 here
            cmd.confidence = min(cmd.confidence, 0.4)

    if cmd.slots.get("product"):
        row, score, ties = _match(cmd.slots["product"], db.products())
        if row is not None:
            cmd.slots["product_id"] = row["id"]
            cmd.slots["product_name"] = row["name_en"]
            if ties:
                cmd.slots["ambiguous_product"] = [
                    t["name_en"] for t in [row] + ties]
                cmd.confidence = min(cmd.confidence, 0.55)
        else:
            cmd.unresolved.append("product")
            cmd.slots["near_product"] = [r["name_en"] for r in ties]
            cmd.confidence = min(cmd.confidence, 0.4)
    return cmd


def product_price_paise(db: Ledger, product_id: int) -> int:
    """Seed-time unit price for a product (paise), 0 if unknown."""
    import sqlite3
    row = db.conn.execute(
        "SELECT amount_paise FROM transactions WHERE product_id=? "
        "AND amount_paise>0 AND qty>0 ORDER BY ts DESC LIMIT 1",
        (product_id,)).fetchone()
    if row:
        qty_row = db.conn.execute(
            "SELECT qty FROM transactions WHERE product_id=? "
            "AND amount_paise>0 AND qty>0 ORDER BY ts DESC LIMIT 1",
            (product_id,)).fetchone()
        if qty_row and qty_row["qty"]:
            return int(row["amount_paise"] / qty_row["qty"])
    return 0
