"""Seed the Bolta Khata ledger DB. Usage: seed_ledger.py [--db PATH] [--fresh]"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bolta.ledger import Ledger
from bolta.seed import seed


def main() -> int:
    db_path = Path(sys.argv[sys.argv.index("--db") + 1]) \
        if "--db" in sys.argv else Path("data/ledger.db")
    if "--fresh" in sys.argv and db_path.exists():
        db_path.unlink()
    db = Ledger(db_path)
    seed(db)
    print(f"products={len(db.products())} customers={len(db.customers())}")
    for c in db.customers()[:6]:
        print(f"  {c['name']}: udhaar ₹{db.balance_paise(c['id']) // 100}")
    db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
