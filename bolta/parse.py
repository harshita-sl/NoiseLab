"""Rules-only intent + entity extraction for Bolta Khata.

Operates on canonical() text: number words are already digits, punctuation
is gone, scripts preserved. Emits Command with unresolved slot *mentions*
— resolve.py maps them to DB rows.

Grammar coverage: Hindi (Devanagari + romanized), English finance words,
Telugu (script). Keep tables additive; never guess silently — a Command
with missing required slots goes to re-ask, not to write.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from noiselab.normalize import canonical

# ------------------------------------------------------------------ tables
UNITS = {
    "kilo": "kg", "kilogram": "kg", "kg": "kg", "किलो": "kg",
    "gram": "g", "gm": "g", "ग्राम": "g",
    "liter": "liter", "litre": "liter", "litr": "liter", "लीटर": "liter",
    "packet": "packet", "paket": "packet", "पैकेट": "packet",
    "carton": "carton", "कार्टन": "carton",
    "dabba": "dabba", "डब्बा": "dabba", "dibba": "dabba",
    "dozen": "dozen", "darjan": "dozen", "dajan": "dozen",
    "दर्जन": "dozen", "डजन": "dozen", "డజన్ల": "dozen",
    "piece": "piece", "pis": "piece",
    "bottle": "bottle", "बोतल": "bottle",
    "cup": "cup", "कप": "cup",
    "sachet": "sachet",
    "box": "box", "बक्सा": "box",
    "కిలో": "kg", "కిలోల": "kg", "కిలోలు": "kg", "లీటరు": "liter",
    "లీటర్లు": "liter", "ప్యాకెట్": "packet",
    "ప్యాకెట్లు": "packet", "కార్టన్": "carton", "కార్టన్ల": "carton",
    "కార్టన్లు": "carton", "కాటన్ల": "carton", "కాటన్": "carton",
    "daba": "dabba", "dabba": "dabba", "डब्बा": "dabba",
}

MONEY_WORDS = {"rupaye", "rupya", "rupay", "paisa", "paise", "rs", "rupees",
               "rupayalu", "rupayi", "रुपये", "रुपए", "रूपये", "पैसे",
               "रुपया", "రూపాయలు", "రూపాయి", "రూపాయ"}

QUESTION_WORDS = {"kitna", "kitni", "kitne", "kya", "कितना", "कितनी",
                  "कितने", "क्या", "ఎంత", "ఎన్ని", "ఏమి",
                  "entha", "enni", "emiti", "ela"}

WORDS = {
    "udhaar": {"udhaar", "udhar", "baki", "baaki", "bakaya", "balance",
               "उधार", "बाकी", "बकाया", "बैलेंस", "అప్పు", "బాకీ",
               "appu"},
    "stock": {"stock", "bacha", "bachi", "bache", "bachcha", "bachchi",
              "baki", "hai", "pada", "pade", "padi", "स्टॉक", "बचा",
              "बची", "बचे", "पड़ा", "पड़े", "पड़ी", "మిగిల", "ఉన్నాయి",
              "స్టాక్", "మిగిలాయి", "మిగిలినాయి", "మిగిలింది"},
    "give_pay": {"diya", "diye", "jama", "paid", "bhara", "bhare", "de",
                 "diyaa", "dene", "denge", "दिया", "दिए", "जमा", "भरा",
                 "भरे", "दिया", "देने",
                 "ఇచ్చాడు", "ఇచ్చారు", "ఇచ్చింది", "చెల్లించారు",
                 "ivvali", "ichaaru", "ichindi", "ivvu", "ivvandi",
                 "icheyam", "dene hai", "dene hain",
                 "జమ", "చేశాడు", "చేసాను", "చేసింది", "చెల్లించింది",
                 "ichchar", "ichar",
                 "deduct", "deducted", "katao", "kaato", "minus",
                 "reduce", "घटाओ", "घटा", "काटो", "काटें", "कटाओ"},
    "take_buy": {"liya", "liye", "le", "khareeda", "kharida", "teesukunda",
                 "teesukundi", "लिया", "लिए", "खरीदा", "खरीदी", "ली",
                 "తీసుకుంది", "తీసుకున్నాడు"},
    "sold": {"bika", "biki", "bike", "bik", "sold", "becha", "bechi", "gay",
             "gaya", "gayi", "gaye", "बिका", "बिकी", "बिके", "बिक", "गया",
             "गई", "गए", "बेचा", "बेची", "अम్మాను",
             "అమ్మేశాను", "అమ్ముడయ్యింది", "అమ్మకం", "bick",
             "అమ్ముడైంది", "అమ్ముడాయి", "అమ్మేశాడు"},
    "purchase": {"mangaya", "mangwana", "mangwani", "mangao", "mangau",
                 "order", "aaya", "aayi", "aane", "aaye", "आए", "मंगवाया",
                 "मंगवानी",
                 "मंगाओ", "मंगाऊ", "ऑर्डर", "आया", "आयी", "ఆర్డర్",
                 "మంగించాను", "వచ్చాయి", "వచ్చింది",
                 "mangvani", "mangavana", "mangava", "aye", "ayye",
                 "मंगवाओ", "మంగించండి", "మంగించావు"},
    "suggest": {"karna chahiye", "kya order", "kya mangau", "kya mangwana",
                "suggest", "kya mangana", "mangana chahiye",
                "kya lena chahiye", "kya order karna chahiye",
                "क्या ऑर्डर", "क्या मंगाऊ", "क्या मंगवाना",
                "क्या मंगाना", "కొనాలి", "ఏమి ఆర్డర్"},
    "adjust": {"update", "adjust", "set", "badlo", "badal", "likhdo",
               "अपडेट", "बदलो", "बदल", "दर्ज"},
}

CASE_MARKERS = {"ne", "ka", "ki", "ko", "ke", "ने", "का", "की", "को", "के",
                "కి", "కు", "యొక్క", "ki"}
STOPWORDS = (CASE_MARKERS | MONEY_WORDS | QUESTION_WORDS | {
    "hai", "hain", "ho", "hua", "karo", "kar", "do", "dena", "deta",
    "batao", "bata", "check", "bhai", "please", "aur", "se", "tak",
    "mein", "main", "the", "a", "ab", "abhi", "ek", "pe", "par", "ko",
    "samaan", "saman", "सामान", "సామాను", "पर", "पे", "है", "हैं", "हो",
    "करो", "कर", "दो", "देना", "बताओ", "और", "से", "में", "उన్నాయి",
    "khata", "khate", "khaata", "bahi", "खाता", "खाते", "बही",
    "arre", "are", "toh", "na", "acha", "accha", "yaar", "अरे", "तो",
    "invoice", "number", "bill", "percent", "refund", "wala", "wali",
    "hoga", "hogi", "scene", "नंबर", "नम्बर",
    "చెప్పు", "లో", "ఉంది", "ఉందా", "ఉన్నాది", "ఉన్నావా"})

CONFIRM_WORDS = {"haan", "ha", "han", "sahi", "theek", "ok", "yes", "sare",
                 "correct", "हाँ", "हां", "सही", "ठीक", "ओके", "అవును",
                 "సరే", "అవునా", "saare", "rai"}
DENY_WORDS = {"nahi", "nahin", "na", "galat", "wrong", "cancel", "नहीं",
              "गलत", "कैंसल", "కాదు", "వద్దు"}
UNDO_WORDS = {"undo", "wapas", "wapis", "piche", "hatao", "vapas",
              "पीछे", "वापस", "हटाओ", "అన్డు", "తిరిగి", "రద్దు",
              "andukaro", "andu", "undu"}


@dataclass
class Command:
    intent: str = "unknown"
    slots: dict = field(default_factory=dict)
    confidence: float = 1.0
    raw: str = ""
    unresolved: list[str] = field(default_factory=list)

    def need(self, *slot_names: str) -> bool:
        return all(self.slots.get(s) for s in slot_names)


_NUM = re.compile(r"^\d+(?:\.\d+)?$")


def _numbers(tokens: list[str]) -> list[tuple[int, str]]:
    return [(i, t) for i, t in enumerate(tokens) if _NUM.match(t)]


def _extract_amounts_quantities(tokens: list[str]):
    """Return (amount, qty, unit, consumed_idx)."""
    amount = qty = None
    unit = None
    consumed: set[int] = set()
    for i, t in _numbers(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        prv = tokens[i - 1] if i > 0 else ""
        if nxt in UNITS:
            qty, unit = float(t), UNITS[nxt]
            consumed |= {i, i + 1}
        elif nxt in MONEY_WORDS or prv in MONEY_WORDS or t.startswith("₹"):
            amount = float(t)
            consumed.add(i)
        elif nxt in WORDS["give_pay"] or prv in WORDS["give_pay"]:
            amount = float(t)  # "paanch sau diye" -> paid 500
            consumed.add(i)
        elif prv in ("number", "invoice", "bill", "नंबर", "నంబర్"):
            consumed.add(i)  # identifier, not money/qty
        elif nxt in ("ka", "ki", "के", "की") and i + 2 < len(tokens) \
                and tokens[i + 2] not in WORDS["udhaar"]:
            amount = float(t)  # "500 ka samaan" -> price
            consumed.add(i)
        elif nxt in WORDS["adjust"] or prv in WORDS["adjust"] \
                or nxt in WORDS["udhaar"] or prv in WORDS["udhaar"]:
            amount = float(t)  # "udhaar 500 update" -> 500 rupees
            consumed.add(i)
    return amount, qty, unit, consumed


_ERGATIVE = {"ne", "ने"}
_POSSESSIVE = {"ka", "ki", "ko", "के", "की", "को", "కు", "కి", "యొక్క"}
_HONORIFIC = {"ji", "जी", "గారు", "sahab", "saab", "sir", "madam"}


def _extract_name(tokens: list[str], consumed: set[int]) -> tuple[str, set[int]]:
    """Name = token before 'ne' (subject) or before 'ka/ki' + udhaar-word.

    'maggi ke 20 packet' must NOT yield 'maggi' as a person — possessive
    markers only count when followed by an udhaar/balance word.
    """
    for i, t in enumerate(tokens):
        if i == 0 or tokens[i - 1] in consumed:
            continue
        nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
        if t in _ERGATIVE or (t in _POSSESSIVE and nxt in WORDS["udhaar"]):
            cand = tokens[i - 1]
            # "geeta ji ke" -> the name is geeta, not ji
            if cand in _HONORIFIC and i - 2 >= 0 \
                    and i - 2 not in consumed:
                return tokens[i - 2], {i - 2}
            return cand, {i - 1}
    return "", set()


def parse(text: str, lang: str = "") -> Command:
    """Parse raw transcript (any script) into a Command. Never raises."""
    canon = canonical(text)
    tokens = canon.split()
    cmd = Command(raw=canon)

    if not tokens:
        cmd.confidence = 0.0
        return cmd

    toks = set(tokens)
    if toks & CONFIRM_WORDS and len(tokens) <= 6:
        cmd.intent = "confirm"
        return cmd
    if toks & DENY_WORDS and len(tokens) <= 6:
        cmd.intent = "deny"
        return cmd
    if toks & UNDO_WORDS:
        cmd.intent = "undo"
        return cmd

    joined = " " + canon + " "
    if any(" " + p + " " in joined or joined.startswith(" " + p)
           for p in WORDS["suggest"]):
        cmd.intent = "reorder_suggestion"
        return cmd

    amount, qty, unit, consumed = _extract_amounts_quantities(tokens)
    name, name_idx = _extract_name(tokens, consumed)
    consumed |= name_idx
    leftover = [t for i, t in enumerate(tokens)
                if i not in consumed and t not in STOPWORDS
                and t not in UNITS and not _NUM.match(t)
                and not any(t in v for v in WORDS.values())]

    is_question = bool(toks & QUESTION_WORDS)
    has_udhaar = bool(toks & WORDS["udhaar"])
    # imperative udhaar verbs count as questions: "udhaar likho" = what's
    # the balance
    if toks & {"likho", "likh", "batao", "bata", "cheppu", "చెప్పు"}:
        is_question = True
    # 'hai' alone is too common to count as a stock signal
    has_stock = bool(toks & (WORDS["stock"] - {"hai"}))
    has_pay = bool(toks & WORDS["give_pay"])
    has_buy = bool(toks & WORDS["take_buy"])
    has_sold = bool(toks & WORDS["sold"])
    has_purchase = bool(toks & WORDS["purchase"])
    has_adjust = bool(toks & WORDS["adjust"])

    # "udhaar 500 update/adjust/set karo" -> credit sale (generic); qty +
    # adjust -> restock. Imperative adjust beats question-shaped fallbacks.
    if has_adjust and amount is not None and (has_udhaar or name):
        cmd.intent = "record_sale"
        if not name and leftover:
            name = leftover[0]
        cmd.slots.update(customer=name, amount=int(amount * 100),
                         credit=True)
        cmd.confidence = 0.8 if name else 0.5
    elif has_adjust and qty is not None and leftover:
        cmd.intent = "add_purchase"
        cmd.slots["product"] = " ".join(leftover)
        cmd.slots["qty"], cmd.slots["unit"] = qty, unit
        cmd.confidence = 0.85
    elif is_question and has_udhaar:
        cmd.intent = "check_credit"
        cmd.slots["customer"] = name or (leftover[0] if leftover else "")
        cmd.confidence = 0.9 if cmd.slots["customer"] else 0.4
    elif has_stock and (leftover or name) and not has_purchase \
            and not has_sold:
        cmd.intent = "check_stock"
        cmd.slots["product"] = " ".join(leftover) or name
        cmd.confidence = 0.9 if is_question else 0.8
    elif amount is not None and not has_buy and not has_sold \
            and (has_pay or name):
        cmd.intent = "record_payment"
        # Telugu/verb-final speech may carry no case marker: fall back to
        # first leftover token as the customer mention.
        if not name and leftover:
            name = leftover[0]
        cmd.slots.update(customer=name, amount=int(amount * 100))
        cmd.confidence = 0.95 if name else 0.5
    elif has_purchase and (qty is not None or "stock" in toks):
        # restock needs a quantity or explicit 'stock mein ... aaya'
        cmd.intent = "add_purchase"
        cmd.slots["product"] = " ".join(leftover)
        if qty is not None:
            cmd.slots["qty"], cmd.slots["unit"] = qty, unit
        cmd.confidence = 0.9
    elif has_sold or (has_buy and (qty is not None or amount is not None)):
        cmd.intent = "record_sale"
        cmd.slots["product"] = " ".join(leftover)
        if name:
            cmd.slots["customer"] = name
        if qty is not None:
            cmd.slots["qty"], cmd.slots["unit"] = qty, unit
        if amount is not None:
            cmd.slots["amount"] = int(amount * 100)
        if has_udhaar or "udhaar" in toks:
            cmd.slots["credit"] = True
        cmd.confidence = 0.85
    else:
        # entity-driven fallback: entities resolved but no verb matched —
        # propose the most plausible low-confidence action rather than
        # giving up. The confirmation card still gates any write.
        cand_name = name or (leftover[0] if leftover else "")
        cand_amount = amount
        if cand_amount is None:
            free = [t for i, t in _numbers(tokens) if i not in consumed
                    and (i + 1 >= len(tokens)
                         or tokens[i + 1] != "percent")]
            if free:
                cand_amount = float(free[0])
        if has_udhaar and cand_name:
            cmd.intent = "check_credit"
            cmd.slots["customer"] = cand_name
            cmd.confidence = 0.55
        elif cand_amount is not None and cand_name:
            cmd.intent = "record_payment"
            cmd.slots.update(customer=cand_name,
                             amount=int(cand_amount * 100))
            cmd.confidence = 0.4
        elif qty is not None and leftover:
            cmd.intent = "record_sale"
            cmd.slots["product"] = " ".join(leftover)
            cmd.slots["qty"], cmd.slots["unit"] = qty, unit
            cmd.confidence = 0.4
        else:
            cmd.confidence = 0.0

    # required-slot check drops confidence, never invents values
    required = {"record_payment": ("customer", "amount"),
                "record_sale": ("product",),
                "add_purchase": ("product",),
                "check_stock": ("product",),
                "check_credit": ("customer",)}
    for slot in required.get(cmd.intent, ()):
        if not cmd.slots.get(slot):
            cmd.slots.pop(slot, None)
            cmd.unresolved.append(slot)
            cmd.confidence = min(cmd.confidence, 0.45)
    # generic-merchandise credit sale: amount + customer is enough to debit
    # ("Sunita ne 1500 ka samaan liya udhaar pe" — no specific product)
    if cmd.intent == "record_sale" and "product" in cmd.unresolved \
            and cmd.slots.get("amount") and cmd.slots.get("customer"):
        cmd.unresolved.remove("product")
        cmd.slots["credit"] = True
        cmd.confidence = 0.7
    return cmd


# Back-compat alias used by tests/docs
parse_command = parse
