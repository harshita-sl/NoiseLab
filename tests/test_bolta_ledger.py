"""ledger.py — txn/balance/undo invariants on a temp DB."""

import pytest

from bolta.ledger import Ledger


@pytest.fixture
def db(tmp_path):
    d = Ledger(tmp_path / "t.db")
    yield d
    d.close()


def test_payment_reduces_balance(db):
    cid = db.add_customer("Test", aliases="test")
    pid = db.add_product("X", unit="piece", stock=10)
    db.record_sale(pid, 2, customer_id=cid, amount_paise=10000, credit=True)
    assert db.balance_paise(cid) == 10000
    db.record_payment(cid, 4000)
    assert db.balance_paise(cid) == 6000


def test_sale_reduces_stock(db):
    pid = db.add_product("X", unit="kg", stock=10)
    db.record_sale(pid, 2.5)
    assert db.stock(pid) == 7.5


def test_purchase_adds_stock(db):
    pid = db.add_product("X", unit="kg", stock=10)
    db.add_purchase(pid, 5)
    assert db.stock(pid) == 15


def test_amount_only_credit_sale(db):
    cid = db.add_customer("Test")
    tid = db.record_sale(None, None, customer_id=cid,
                         amount_paise=150000, credit=True)
    assert tid
    assert db.balance_paise(cid) == 150000


def test_undo_restores_stock_and_balance(db):
    cid = db.add_customer("Test")
    pid = db.add_product("X", unit="kg", stock=10)
    db.record_sale(pid, 2, customer_id=cid, amount_paise=9000, credit=True)
    assert db.stock(pid) == 8 and db.balance_paise(cid) == 9000
    undone = db.undo_last()
    assert undone["kind"] == "credit_sale"
    assert db.stock(pid) == 10 and db.balance_paise(cid) == 0


def test_undo_payment_restores_balance(db):
    cid = db.add_customer("Test")
    db._txn("credit_sale", customer_id=cid, amount_paise=5000,
            source="seed")
    db.record_payment(cid, 2000)
    assert db.balance_paise(cid) == 3000
    db.undo_last()
    assert db.balance_paise(cid) == 5000


def test_undo_empty_is_none(db):
    assert db.undo_last() is None


def test_audit_written(db):
    cid = db.add_customer("Test")
    aid = db.propose({"intent": "record_payment"})
    tid = db.record_payment(cid, 1000)
    db.mark_confirmed(aid, tid)
    rows = db.conn.execute("SELECT action FROM audit_log").fetchall()
    assert [r["action"] for r in rows] == ["propose", "confirm"]
