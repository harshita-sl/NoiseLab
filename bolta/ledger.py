"""SQLite ledger for Bolta Khata.

Tables: products, customers, transactions, audit_log.
Amounts are integer paise. Undo writes a compensating transaction
(source='undo') — rows are never deleted or mutated except status flags.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY,
    name_en TEXT NOT NULL,
    name_hi TEXT,
    aliases TEXT DEFAULT '',
    unit TEXT NOT NULL DEFAULT 'piece',
    pack_size INTEGER DEFAULT 1,
    stock REAL DEFAULT 0,
    reorder_point REAL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    aliases TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    kind TEXT NOT NULL,           -- sale|credit_sale|payment|purchase
    customer_id INTEGER,
    product_id INTEGER,
    qty REAL,
    unit TEXT,
    amount_paise INTEGER DEFAULT 0,
    note TEXT DEFAULT '',
    source TEXT DEFAULT 'voice',  -- voice|seed|undo
    status TEXT DEFAULT 'ok',     -- ok|undone|void
    audio_hash TEXT,
    transcript TEXT
);
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY,
    ts REAL NOT NULL,
    action TEXT NOT NULL,         -- propose|confirm|deny|undo
    txn_id INTEGER,
    payload TEXT DEFAULT ''
);
"""


class Ledger:
    def __init__(self, path: str | Path = "data/ledger.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.path))
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------- catalog
    def add_product(self, name_en: str, name_hi: str = "", *,
                    aliases: str = "", unit: str = "piece",
                    pack_size: int = 1, stock: float = 0.0,
                    reorder_point: float = 0.0) -> int:
        cur = self.conn.execute(
            "INSERT INTO products (name_en,name_hi,aliases,unit,pack_size,"
            "stock,reorder_point) VALUES (?,?,?,?,?,?,?)",
            (name_en, name_hi, aliases, unit, pack_size, stock,
             reorder_point))
        self.conn.commit()
        return cur.lastrowid

    def add_customer(self, name: str, *, aliases: str = "") -> int:
        cur = self.conn.execute(
            "INSERT INTO customers (name,aliases) VALUES (?,?)",
            (name, aliases))
        self.conn.commit()
        return cur.lastrowid

    def products(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM products").fetchall()

    def customers(self) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM customers").fetchall()

    # ----------------------------------------------------------- txns
    def _txn(self, kind: str, *, customer_id: int | None = None,
             product_id: int | None = None, qty: float | None = None,
             unit: str | None = None, amount_paise: int = 0,
             note: str = "", source: str = "voice",
             audio_hash: str | None = None,
             transcript: str | None = None) -> int:
        cur = self.conn.execute(
            "INSERT INTO transactions (ts,kind,customer_id,product_id,qty,"
            "unit,amount_paise,note,source,audio_hash,transcript) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), kind, customer_id, product_id, qty, unit,
             amount_paise, note, source, audio_hash, transcript))
        self.conn.commit()
        return cur.lastrowid

    def record_sale(self, product_id: int, qty: float, *,
                    customer_id: int | None = None,
                    amount_paise: int = 0, credit: bool = False,
                    unit: str = "piece", note: str = "",
                    source: str = "voice",
                    audio_hash: str | None = None,
                    transcript: str | None = None) -> int:
        """Record a sale; subtracts stock. credit=True -> adds to udhaar."""
        kind = "credit_sale" if credit else "sale"
        tid = self._txn(kind, customer_id=customer_id, product_id=product_id,
                        qty=qty, unit=unit, amount_paise=amount_paise,
                        note=note, source=source, audio_hash=audio_hash,
                        transcript=transcript)
        if product_id is not None and qty is not None:
            self.conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id=?",
                (qty, product_id))
            self.conn.commit()
        return tid

    def record_payment(self, customer_id: int, amount_paise: int, *,
                       note: str = "", source: str = "voice",
                       audio_hash: str | None = None,
                       transcript: str | None = None) -> int:
        """Customer pays toward their udhaar."""
        return self._txn("payment", customer_id=customer_id,
                         amount_paise=amount_paise, note=note, source=source,
                         audio_hash=audio_hash, transcript=transcript)

    def add_purchase(self, product_id: int, qty: float, *,
                     unit: str = "piece", amount_paise: int = 0,
                     note: str = "", source: str = "voice",
                     audio_hash: str | None = None,
                     transcript: str | None = None) -> int:
        """Stock arrives from supplier; adds to stock."""
        tid = self._txn("purchase", product_id=product_id, qty=qty, unit=unit,
                        amount_paise=amount_paise, note=note, source=source,
                        audio_hash=audio_hash, transcript=transcript)
        self.conn.execute("UPDATE products SET stock = stock + ? WHERE id=?",
                          (qty, product_id))
        self.conn.commit()
        return tid

    # ------------------------------------------------------------ queries
    def balance_paise(self, customer_id: int) -> int:
        """Outstanding udhaar: credit sales minus payments (ok txns only)."""
        row = self.conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN kind='credit_sale' "
            "THEN amount_paise WHEN kind='payment' THEN -amount_paise "
            "ELSE 0 END),0) AS bal FROM transactions "
            "WHERE customer_id=? AND status='ok'",
            (customer_id,)).fetchone()
        return int(row["bal"])

    def stock(self, product_id: int) -> float:
        row = self.conn.execute(
            "SELECT stock FROM products WHERE id=?", (product_id,)).fetchone()
        return float(row["stock"]) if row else 0.0

    def recent(self, limit: int = 20) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT t.*, c.name AS customer_name, p.name_en AS product_name "
            "FROM transactions t "
            "LEFT JOIN customers c ON c.id=t.customer_id "
            "LEFT JOIN products p ON p.id=t.product_id "
            "WHERE t.status='ok' ORDER BY t.ts DESC LIMIT ?",
            (limit,)).fetchall()

    def sales_history(self, product_id: int, days: int = 14) -> float:
        """Units sold in last `days` days (ok txns, seeded + voice)."""
        cutoff = time.time() - days * 86400
        row = self.conn.execute(
            "SELECT COALESCE(SUM(qty),0) AS u FROM transactions "
            "WHERE product_id=? AND kind IN ('sale','credit_sale') "
            "AND status='ok' AND ts>=?",
            (product_id, cutoff)).fetchone()
        return float(row["u"])

    # ---------------------------------------------------------------- undo
    def _audit(self, action: str, txn_id: int | None,
               payload: dict[str, Any]) -> None:
        self.conn.execute(
            "INSERT INTO audit_log (ts,action,txn_id,payload) VALUES (?,?,?,?)",
            (time.time(), action, txn_id, json.dumps(payload,
                                                     ensure_ascii=False)))
        self.conn.commit()

    def propose(self, payload: dict[str, Any]) -> int:
        """Log a proposed action (before confirmation)."""
        cur = self.conn.execute(
            "INSERT INTO audit_log (ts,action,txn_id,payload) "
            "VALUES (?,?,-1,?)",
            (time.time(), "propose", json.dumps(payload, ensure_ascii=False)))
        self.conn.commit()
        return cur.lastrowid

    def mark_confirmed(self, audit_id: int, txn_id: int) -> None:
        self._audit("confirm", txn_id, {"propose_id": audit_id})

    def mark_denied(self, audit_id: int) -> None:
        self._audit("deny", None, {"propose_id": audit_id})

    def undo_last(self) -> sqlite3.Row | None:
        """Reverse the most recent ok voice/seed txn. Returns the undo row."""
        row = self.conn.execute(
            "SELECT * FROM transactions WHERE status='ok' "
            "ORDER BY ts DESC LIMIT 1").fetchone()
        if row is None:
            return None
        self.conn.execute("UPDATE transactions SET status='undone' WHERE id=?",
                          (row["id"],))
        if row["kind"] in ("sale", "credit_sale") and row["product_id"]:
            self.conn.execute(
                "UPDATE products SET stock = stock + ? WHERE id=?",
                (row["qty"], row["product_id"]))
        elif row["kind"] == "purchase" and row["product_id"]:
            self.conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id=?",
                (row["qty"], row["product_id"]))
        self.conn.commit()
        self._audit("undo", row["id"], dict(row))
        return row
