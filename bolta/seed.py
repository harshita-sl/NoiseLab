"""Synthetic seed data for Bolta Khata — no real people, no real numbers.

Products are generic kirana staples; customers are common first-name
labels only (synthetic, per challenge rules). Sales history is generated
with a seeded RNG so every machine builds the identical DB.
"""

from __future__ import annotations

import time

import numpy as np

from bolta.ledger import Ledger

# (name_en, name_hi, aliases comma-sep, unit, pack_size, stock, reorder_pt,
#  price_paise, avg_daily_sales)
PRODUCTS = [
    ("Maggi", "मैगी", "maggi,megi,maggi noodles,मैगी नूडल्स,మ్యాగీ", "packet", 12, 60, 24, 1400, 8),
    ("Aata", "आटा", "aata,atta,wheat flour,गेहूं आटा,గోధుమ పిండి", "kg", 1, 30, 10, 5500, 3),
    ("Chawal", "चावल", "chawal,chaval,rice,बासमती,రైస్,బియ్యం", "kg", 1, 40, 15, 7000, 4),
    ("Daal", "दाल", "daal,dal,toor dal,arhar,अरहर,పప్పు", "kg", 1, 20, 8, 14000, 2),
    ("Chini", "चीनी", "chini,cheeni,sugar,చక్కెర", "kg", 1, 25, 10, 4500, 2),
    ("Tel", "तेल", "tel,oil,refined oil,sarso,నూనె", "liter", 1, 15, 6, 18000, 1),
    ("Coke", "कोक", "coke,coca cola,cola,कोका कोला,కోక్", "bottle", 12, 36, 12, 4000, 5),
    ("Parle-G", "पारले जी", "parle,parle g,parle-g,parleji,biscuit,బిస్కెట్", "packet", 12, 80, 24, 1000, 10),
    ("Doodh", "दूध", "doodh,dudh,milk,amul milk,పాలు,మిల్క్", "packet", 1, 20, 10, 2700, 12),
    ("Dahi", "दही", "dahi,curd,amul dahi,పెరుగు", "cup", 1, 15, 6, 3000, 4),
    ("Sabun", "साबुन", "sabun,soap,lux,dettol soap,సబ్బు", "piece", 4, 20, 8, 3500, 2),
    ("Shampoo", "शैम्पू", "shampoo,clinic plus,sachet,షాంపూ", "sachet", 16, 50, 16, 200, 6),
    ("Anda", "अंडा", "anda,eggs,egg,अंडे,గుడ్లు", "dozen", 1, 6, 4, 7800, 2),
    ("Pav", "पाव", "pav,bread,pav bread,bun,బ్రెడ్", "piece", 4, 16, 8, 1200, 6),
    ("Chai Patti", "चाय पत्ती", "chai,tea,chai patti,tata tea,red label,టీ", "packet", 1, 12, 5, 15000, 1),
    ("Namkeen", "नमकीन", "namkeen,bhujia,haldiram", "packet", 6, 30, 12, 2000, 4),
    ("Bidi Cell", "सेल", "cell,battery,aa cell,batteries", "piece", 2, 24, 10, 2000, 1),
    ("Matchbox", "माचिस", "matchbox,machis,diye", "box", 10, 40, 10, 200, 2),
    ("Surf", "सर्फ", "surf,surf excel,detergent,washing powder", "packet", 6, 18, 6, 11500, 1),
    ("Toothpaste", "टूथपेस्ट", "toothpaste,colgate,pepsodent,paste", "piece", 6, 18, 6, 10000, 1),
    ("Kurkure", "कुरकुरे", "kurkure,chips,lays,snacks", "packet", 12, 48, 12, 2000, 5),
    ("Ghee", "घी", "ghee,amul ghee,deshi ghee", "dabba", 1, 8, 3, 65000, 0.5),
    ("Besan", "बेसन", "besan,gram flour,chana flour", "kg", 1, 10, 4, 8000, 1),
    ("Masala", "मसाला", "masala,spices,haldi,mirchi powder", "packet", 1, 25, 10, 5000, 3),
    ("Maggi Sauce", "सॉस", "sauce,tomato sauce,maggi sauce,ketchup", "bottle", 1, 10, 4, 13000, 0.5),
]

# (name, aliases) — synthetic first names only; incl. Telugu script so
# te-IN transcripts resolve (రాహుల్ -> Rahul)
CUSTOMERS = [
    ("Rahul", "rahul,राहुल,rahul sharma,రాహుల్"),
    ("Sunita", "sunita,सुनीता,sunita devi,సునీత"),
    ("Ramesh", "ramesh,रमेश,ramesh bhai,రమేష్"),
    ("Lakshmi", "lakshmi,लक्ष्मी,laxmi,లక్ష్మీ"),
    ("Kaka", "kaka,काका,kaka ji,కాకా"),
    ("Priya", "priya,प्रिया,ప్రియా"),
    ("Mohan", "mohan,मोहन,mohan lal,మోహన్"),
    ("Geeta", "geeta,गीता,gita,గీత"),
    ("Vijay", "vijay,विजय,vijay bhai,విజయ్"),
    ("Fatima", "fatima,फातिमा,fatima begum,ఫాతిమా"),
    ("Suresh", "suresh,सुरेश,సురేష్"),
    ("Anita", "anita,अनीता,anita aunty,అనిత"),
]


def seed(db: Ledger, *, days: int = 90, seed: int = 42) -> None:
    """Populate products, customers, and `days` of synthetic sales history.

    Idempotent: skips seeding if products already exist.
    """
    if db.products():
        return
    g = np.random.default_rng(seed)
    prod_ids = {}
    for (en, hi, aliases, unit, pack, stock, rp, _price, _avg) in PRODUCTS:
        pid = db.add_product(en, hi, aliases=aliases, unit=unit,
                             pack_size=pack, stock=stock, reorder_point=rp)
        prod_ids[en] = pid
    cust_ids = [db.add_customer(n, aliases=a) for n, a in CUSTOMERS]

    now = time.time()
    for (en, _hi, _al, unit, _pack, _st, _rp, price, avg) in PRODUCTS:
        pid = prod_ids[en]
        for d in range(days, 0, -1):
            dow = time.localtime(now - d * 86400).tm_wday
            lam = avg * (1.35 if dow >= 5 else 1.0)  # weekend bump
            units = int(g.poisson(lam))
            if units <= 0:
                continue
            kind = "credit_sale" if g.random() < 0.15 else "sale"
            db.conn.execute(
                "INSERT INTO transactions (ts,kind,customer_id,product_id,"
                "qty,unit,amount_paise,note,source,status) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (now - d * 86400 - float(g.integers(0, 43200)),
                 kind,
                 int(cust_ids[g.integers(0, len(cust_ids))])
                 if kind == "credit_sale" else None,
                 pid, float(units), unit, int(units * price),
                 "", "seed", "ok"))
        db.conn.commit()

    # A few udhaar balances so check_credit demos well
    for cid in cust_ids[:6]:
        amt = int(g.integers(1, 30)) * 10000  # ₹100–3000 in paise
        db._txn("credit_sale", customer_id=cid, amount_paise=amt,
                note="seed udhaar", source="seed")
        if g.random() < 0.5:
            db._txn("payment", customer_id=cid,
                    amount_paise=amt // 2, note="seed part-payment",
                    source="seed")
