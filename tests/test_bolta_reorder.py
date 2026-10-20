"""reorder.py — formulas verified against hand-computed values."""

import time

import pytest

from bolta.ledger import Ledger
from bolta.reorder import suggestions


@pytest.fixture
def db(tmp_path):
    d = Ledger(tmp_path / "t.db")
    pid = d.add_product("Milk", unit="packet", pack_size=1, stock=10)
    now = time.time()
    # 14 days x 2 units/day = 28 units -> daily_rate = 2.0
    for day in range(14):
        d.conn.execute(
            "INSERT INTO transactions (ts,kind,product_id,qty,unit,"
            "amount_paise,source,status) VALUES (?,?,?,?,?,?,?,?)",
            (now - day * 86400, "sale", pid, 2.0, "packet", 5400,
             "seed", "ok"))
    d.conn.commit()
    yield d
    d.close()


def test_reorder_triggers_and_qty(db):
    # rate=2/day, stock=10, horizon=5 -> days_left=5.0 -> NOT < 5 (edge: equal)
    sugg = suggestions(db, days=14, lead_time=2, safety_days=3)
    assert sugg == [] or sugg[0]["days_left"] == 5.0
    # bump stock down -> now inside horizon
    pid = db.products()[0]["id"]
    db.conn.execute("UPDATE products SET stock=8 WHERE id=?", (pid,))
    db.conn.commit()
    sugg = suggestions(db, days=14)
    assert sugg and sugg[0]["name_en"] == "Milk"
    # need = 2*5 - 8 = 2 -> qty >= 2, pack=1
    assert sugg[0]["qty"] >= 2
    assert sugg[0]["days_left"] == 4.0


def test_pack_rounding(db):
    pid = db.products()[0]["id"]
    db.conn.execute(
        "UPDATE products SET stock=1, pack_size=6 WHERE id=?", (pid,))
    db.conn.commit()
    sugg = suggestions(db, days=14)
    # need = 2*5 - 1 = 9 -> ceil(9/6)*6 = 12
    assert sugg[0]["qty"] == 12


def test_no_sales_no_reorder(tmp_path):
    d = Ledger(tmp_path / "t2.db")
    d.add_product("Shelf Warmer", stock=5)
    assert suggestions(d, days=14) == []
    d.close()
