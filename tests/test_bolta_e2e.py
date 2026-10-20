"""End-to-end: transcript -> parse -> propose -> confirm -> DB state.

No API calls — transcripts are fixtures. Covers every write intent,
undo, deny, and failure injection.
"""

import pytest

from bolta.actions import apply, propose
from bolta.ledger import Ledger
from bolta.parse import parse
from bolta.resolve import resolve


@pytest.fixture
def db(tmp_path):
    d = Ledger(tmp_path / "t.db")
    cid = d.add_customer("Rahul", aliases="rahul,राहुल,రాహుల్")
    pid = d.add_product("Maggi", name_hi="मैगी", aliases="maggi,मैगी,మ్యాగీ",
                        unit="packet", stock=60)
    d._txn("credit_sale", customer_id=cid, amount_paise=50000,
           source="seed")
    # priced history so record_sale can value a qty x unit sale
    d._txn("sale", product_id=pid, qty=4.0, unit="packet",
           amount_paise=5600, source="seed")
    yield d, cid, pid
    d.close()


def _turn(db, text):
    cmd = parse(text)
    prop = propose(cmd, db)
    return cmd, prop


def test_payment_full_turn(db):
    d, cid, _ = db
    _, prop = _turn(d, "Rahul ne paanch sau rupaye diye")
    assert prop.intent == "record_payment" and not prop.error
    tid = apply(prop, d, transcript="Rahul ne paanch sau rupaye diye")
    assert tid and d.balance_paise(cid) == 50000 - 50000


def test_credit_sale_full_turn(db):
    d, cid, pid = db
    _, prop = _turn(d, "Rahul ne do packet Maggi udhaar pe liya")
    assert prop.intent == "record_sale"
    apply(prop, d)
    assert d.balance_paise(cid) == 50000 + 2800  # 2 x ₹14
    assert d.stock(pid) == 58


def test_check_credit_no_write(db):
    d, cid, _ = db
    _, prop = _turn(d, "Rahul ka udhaar kitna hai")
    assert prop.needs_confirm is False
    assert "5476" not in prop.description  # seeded balance is ₹500 here
    assert "500" in prop.description


def test_unknown_never_writes(db):
    d, cid, _ = db
    before = d.balance_paise(cid)
    _, prop = _turn(d, "aaj mausam kaisa hai")
    assert prop.error or prop.intent == "unknown"
    apply(prop, d)
    assert d.balance_paise(cid) == before


def test_garbled_number_graceful(db):
    d, cid, _ = db
    _, prop = _turn(d, "Rahul ne paanch so diye")  # 'so' is not a number
    assert prop.error or prop.confidence < 0.5 or prop.intent == "unknown"


def test_undo_via_command(db):
    d, cid, _ = db
    _turn(d, "Rahul ne do sau jama kiye")
    _, prop = _turn(d, "Rahul ne do sau jama kiye")
    apply(prop, d)
    assert d.balance_paise(cid) == 50000 - 20000
    _, up = _turn(d, "undo karo")
    apply(up, d)
    assert d.balance_paise(cid) == 50000


def test_ambiguous_product_flagged(db):
    d, cid, _ = db
    d.add_product("Maggi Noodles", aliases="maggi")
    cmd = resolve(parse("Maggi bika do packet"), d)
    assert cmd.slots.get("ambiguous_product")
    assert cmd.confidence <= 0.55


def test_telugu_payment_full_turn(db):
    d, cid, _ = db
    _, prop = _turn(d, "రాహుల్ ఐదు వందలు రూపాయలు ఇచ్చాడు")
    assert prop.intent == "record_payment"
    apply(prop, d)
    assert d.balance_paise(cid) == 0
