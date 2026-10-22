"""ActionProposal: what a parsed Command would do if confirmed.

propose() never writes — it builds a preview the confirm card shows,
plus the ops to run on accept. Nothing lands in the DB before 'haan'.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bolta.ledger import Ledger
from bolta.parse import Command
from bolta.reorder import suggestions
from bolta.resolve import product_price_paise, resolve
from bolta.say import say_amount, say_hi, say_hinglish


@dataclass
class ActionProposal:
    intent: str
    description: str          # human-readable preview for the confirm card
    spoken_hi: str = ""       # Devanagari read-back text
    spoken_hinglish: str = "" # Romanized read-back text
    confidence: float = 1.0
    needs_confirm: bool = True
    ops: list[dict] = field(default_factory=list)   # executed on accept
    error: str = ""

    def speak(self, lang: str = "hinglish") -> str:
        return self.spoken_hi if lang == "hi" else self.spoken_hinglish


def _money_words(paise: int, lang: str) -> str:
    if paise <= 0:
        return ""
    return say_amount(paise, "hi" if lang == "hi" else "hinglish")


def propose(cmd: Command, db: Ledger) -> ActionProposal:
    """Build the proposal for a (resolved) Command."""
    cmd = resolve(cmd, db)
    s = cmd.slots

    if cmd.unresolved or cmd.intent == "unknown":
        # explain WHICH slot failed + offer near-matches
        bits = []
        for slot in cmd.unresolved:
            heard = s.get(slot, "")
            near = s.get(f"near_{slot}", [])
            if near:
                bits.append(f"{slot} '{heard}' nahi mila — "
                            f"matlab {', '.join(near)}")
            elif heard:
                bits.append(f"{slot} '{heard}' khata mein nahi hai")
            else:
                bits.append(f"{slot} nahi suna")
        if not bits:
            bits.append("command samajh nahi aaya")
        why = "; ".join(bits)
        return ActionProposal(
            intent=cmd.intent, confidence=cmd.confidence,
            description=f"{why}. Dobara bolo — jaise "
                        "'Rahul ne paanch sau diye' ya "
                        "'Maggi kitni bachi hai'.",
            spoken_hi="समझ नहीं आया, दोबारा बोलो।",
            spoken_hinglish="Samajh nahi aaya, dobara bolo.",
            error="unresolved", ops=[])

    if cmd.intent == "record_payment":
        cid, paise = s["customer_id"], int(s["amount"])
        new_bal = db.balance_paise(cid) - paise
        name = s["customer_name"]
        amt_hi, amt_rom = _money_words(paise, "hi"), _money_words(paise, "ro")
        bal_hi, bal_rom = (_money_words(max(new_bal, 0), "hi"),
                           _money_words(max(new_bal, 0), "ro"))
        return ActionProposal(
            intent="record_payment", confidence=cmd.confidence,
            description=f"{name} ne ₹{paise // 100} jama kiye "
                        f"(baaki ₹{max(new_bal, 0) // 100})",
            spoken_hi=(f"{name} ने {amt_hi} जमा किए, अब {bal_hi} बाकी। "
                       "सही है?"),
            spoken_hinglish=(f"{name} ne {amt_rom} jama kiye, "
                             f"ab {bal_rom} baaki. Sahi hai?"),
            ops=[{"kind": "payment", "customer_id": cid,
                  "amount_paise": paise}])

    if cmd.intent == "record_sale":
        pid = s.get("product_id")
        if pid is None and s.get("amount") and s.get("customer_id"):
            # generic credit sale: debit customer, no product/stock line
            amt = int(s["amount"])
            cust = s["customer_name"]
            new_bal = db.balance_paise(s["customer_id"]) + amt
            return ActionProposal(
                intent="record_sale", confidence=cmd.confidence,
                description=f"{cust} ne ₹{amt // 100} ka samaan liya udhaar pe "
                            f"(baaki ₹{new_bal // 100})",
                spoken_hi=(f"{cust} ने {_money_words(amt, 'hi')} का सामान "
                           f"उधार लिया, अब {_money_words(new_bal, 'hi')} "
                           "बाकी। सही है?"),
                spoken_hinglish=(f"{cust} ne {_money_words(amt, 'ro')} ka "
                                 f"samaan udhaar liya, ab "
                                 f"{_money_words(new_bal, 'ro')} baaki. "
                                 "Sahi hai?"),
                ops=[{"kind": "sale", "product_id": None, "qty": None,
                      "unit": None, "amount_paise": amt,
                      "customer_id": s["customer_id"], "credit": True}])
        qty = s.get("qty") or 1.0
        unit = s.get("unit") or "piece"
        price = (product_price_paise(db, pid)
                 if s.get("amount") is None else int(s["amount"] / max(qty, 1)))
        amt = int(price * qty) if s.get("amount") is None else int(s["amount"])
        credit = bool(s.get("credit")) or bool(s.get("customer_id"))
        name = s.get("product_name", s.get("product", "?"))
        cust = s.get("customer_name", "")
        desc = (f"{cust + ' ne ' if cust else ''}{qty:g} {unit} {name} "
                f"{'udhaar pe ' if credit else ''}₹{amt // 100}")
        return ActionProposal(
            intent="record_sale", confidence=cmd.confidence,
            description=desc,
            spoken_hi=(f"{qty:g} {unit} {name} बिका, "
                       f"{_money_words(amt, 'hi')}. सही है?"),
            spoken_hinglish=(f"{qty:g} {unit} {name} bika, "
                             f"{_money_words(amt, 'ro')}. Sahi hai?"),
            ops=[{"kind": "sale", "product_id": pid, "qty": qty,
                  "unit": unit, "amount_paise": amt,
                  "customer_id": s.get("customer_id"),
                  "credit": credit}])

    if cmd.intent == "check_credit":
        bal = db.balance_paise(s["customer_id"])
        name = s["customer_name"]
        return ActionProposal(
            intent="check_credit", confidence=cmd.confidence,
            needs_confirm=False,
            description=f"{name} ka udhaar: ₹{bal // 100}",
            spoken_hi=f"{name} का उधार {_money_words(bal, 'hi')} है।",
            spoken_hinglish=f"{name} ka udhaar {_money_words(bal, 'ro')} hai.")

    if cmd.intent == "check_stock":
        stock = db.stock(s["product_id"])
        name = s["product_name"]
        return ActionProposal(
            intent="check_stock", confidence=cmd.confidence,
            needs_confirm=False,
            description=f"{name}: {stock:g} bacha hai",
            spoken_hi=f"{name} {stock:g} बचा है।",
            spoken_hinglish=f"{name} {stock:g} bacha hai.")

    if cmd.intent == "add_purchase":
        name = s.get("product_name", "?")
        qty = s.get("qty") or 1.0
        unit = s.get("unit") or "piece"
        return ActionProposal(
            intent="add_purchase", confidence=cmd.confidence,
            description=f"{qty:g} {unit} {name} stock mein aaya",
            spoken_hi=f"{qty:g} {unit} {name} आया। सही है?",
            spoken_hinglish=f"{qty:g} {unit} {name} aaya. Sahi hai?",
            ops=[{"kind": "purchase", "product_id": s.get("product_id"),
                  "qty": qty, "unit": unit}])

    if cmd.intent == "reorder_suggestion":
        sugg = suggestions(db, days=14)
        if not sugg:
            return ActionProposal(
                intent="reorder_suggestion", needs_confirm=False,
                description="Kuch order karne ki zaroorat nahi.",
                spoken_hi="कुछ ऑर्डर करने की ज़रूरत नहीं।",
                spoken_hinglish="Kuch order karne ki zaroorat nahi.")
        top = sugg[:5]
        desc = "Order: " + ", ".join(
            f"{x['name_en']} ×{x['qty']}" for x in top)
        spoken = "Order karo: " + ", ".join(
            f"{x['name_en']} {x['qty']} {x['unit']}" for x in top[:3])
        return ActionProposal(
            intent="reorder_suggestion", needs_confirm=False,
            description=desc, spoken_hinglish=spoken,
            spoken_hi=spoken)

    if cmd.intent == "undo":
        return ActionProposal(
            intent="undo", needs_confirm=False,
            description="Last entry undo kar raha hoon",
            spoken_hi="आखिरी एंट्री वापस ले रहा हूँ।",
            spoken_hinglish="Last entry undo kar raha hoon.")

    return ActionProposal(intent=cmd.intent, description="?",
                          error="unhandled")


def apply(proposal: ActionProposal, db: Ledger, *,
          audio_hash: str | None = None, transcript: str | None = None,
          audit_id: int | None = None) -> int | None:
    """Execute proposal ops after user confirmation. Returns txn id."""
    if proposal.intent == "undo":
        undone = db.undo_last()
        return undone["id"] if undone else None
    txn_id = None
    for op in proposal.ops:
        if op["kind"] == "payment":
            txn_id = db.record_payment(
                op["customer_id"], op["amount_paise"],
                audio_hash=audio_hash, transcript=transcript)
        elif op["kind"] == "sale":
            txn_id = db.record_sale(
                op["product_id"], op["qty"],
                customer_id=op.get("customer_id"),
                amount_paise=op["amount_paise"], credit=op["credit"],
                unit=op.get("unit", "piece"),
                audio_hash=audio_hash, transcript=transcript)
        elif op["kind"] == "purchase":
            txn_id = db.add_purchase(
                op["product_id"], op["qty"], unit=op.get("unit", "piece"),
                audio_hash=audio_hash, transcript=transcript)
    if audit_id is not None and txn_id:
        db.mark_confirmed(audit_id, txn_id)
    return txn_id
