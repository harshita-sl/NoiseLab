"""Text normalization for scoring Prisma output against references.

Observed API behaviour (Oct 2026, verified live):
- hi-IN verbatim   -> Devanagari, punctuation kept (। , ?), spelling variants
                      (पाँच/पांच, रुपये/रुपए)
- en-IN verbatim   -> Latin, lowercase, no punctuation; digits spoken by TTS
                      come back as English number words ("five hundred")
- format=transcribe (ITN) -> "₹500", Indian digit grouping, dates/times;
                      response also carries output.literal (raw verbatim)
- itn_native_numerals -> Devanagari digits "₹५,०००"

normalize_text(): script-level cleanup only (case, punctuation, digit script,
spelling variants). canonical(): additionally converts number words to digits
("पाँच सौ" / "five hundred" / "₹500" -> "500"), which makes ITN and verbatim
outputs comparable and enables value-based entity scoring.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------------------
# Character-level fixes
# ---------------------------------------------------------------------------

_DEV_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

# Candrabindu -> anusvara (पाँच == पांच); nukta stripped (ज़ -> ज).
_CHAR_MAP = str.maketrans({
    "ँ": "ं",
    "़": "",
    "।": " ",
    "॥": " ",
    "–": " ",
    "—": " ",
    "-": " ",
    "'": " ",
    "\u2019": " ",
    "\u2018": " ",
})

_WS_RE = re.compile(r"\s+")
# Merge grouped digits: "5,000" / "5,00,000" -> "5000"
_GROUPED_NUM_RE = re.compile(r"(?<=\d),(?=\d)")
_CURRENCY_SYM_RE = re.compile(r"[₹$£€¥¢]")

# Tokens that carry no lexical content for comparison.
_DROP_TOKENS = {"rs", "inr"}

# Observed free spelling variants -> canonical form.
_VARIANTS = {
    "रुपए": "रुपये",
    "रुपया": "रुपये",
    "रुपयों": "रुपये",
    "पैसा": "पैसे",
}


def normalize_text(text: str | None) -> str:
    """Script-level normalization shared by all metrics."""
    if not text:
        return ""
    t = unicodedata.normalize("NFC", text)
    t = t.translate(_DEV_DIGITS)
    t = _CURRENCY_SYM_RE.sub(" ", t)
    t = _GROUPED_NUM_RE.sub("", t)
    t = t.translate(_CHAR_MAP)
    # \w won't keep Indic combining marks (matras), so filter by Unicode
    # category instead: keep letters/marks/numbers, drop punct+symbols.
    t = "".join(
        c if (unicodedata.category(c)[0] in "LMN" or c == "_") else " "
        for c in t
    )
    t = t.lower()
    tokens = [
        _VARIANTS.get(tok, tok)
        for tok in t.split()
        if tok not in _DROP_TOKENS
    ]
    return _WS_RE.sub(" ", " ".join(tokens)).strip()


# ---------------------------------------------------------------------------
# Number words -> digits
# ---------------------------------------------------------------------------

_HI_ONES = {
    "शून्य": 0, "सुन्य": 0, "शुन्य": 0, "एक": 1, "दो": 2, "तीन": 3,
    "चार": 4, "पाँच": 5, "पांच": 5, "छह": 6, "छः": 6, "सात": 7,
    "आठ": 8, "नौ": 9, "दस": 10, "ग्यारह": 11, "ग्यारा": 11,
    "बारह": 12, "बारा": 12, "तेरह": 13, "तेरा": 13, "चौदह": 14,
    "चौदा": 14, "पंद्रह": 15, "पंदरा": 15, "सोलह": 16, "सोला": 16,
    "सत्रह": 17, "सत्रा": 17, "अठारह": 18, "अठारा": 18, "उन्नीस": 19,
    "बीस": 20, "इक्कीस": 21, "बाईस": 22, "तेईस": 23, "चौबीस": 24,
    "पच्चीस": 25, "छब्बीस": 26, "सत्ताईस": 27, "अट्ठाईस": 28,
    "अठ्ठाईस": 28, "उनतीस": 29, "तीस": 30, "इकतीस": 31, "बत्तीस": 32,
    "तैंतीस": 33, "चौंतीस": 34, "पैंतीस": 35, "छत्तीस": 36,
    "सैंतीस": 37, "अड़तीस": 38, "उनतालीस": 39, "चालीस": 40,
    "इकतालीस": 41, "बयालीस": 42, "तैंतालीस": 43, "चवालीस": 44,
    "पैंतालीस": 45, "छियालीस": 46, "सैंतालीस": 47, "अड़तालीस": 48,
    "उनचास": 49, "पचास": 50, "इक्यावन": 51, "बावन": 52,
    "तिरेपन": 53, "तिरपन": 53, "चौवन": 54, "पचपन": 55, "छप्पन": 56,
    "सत्तावन": 57, "अट्ठावन": 58, "उनसठ": 59, "साठ": 60, "इकसठ": 61,
    "बासठ": 62, "तिरेसठ": 63, "तिरसठ": 63, "चौंसठ": 64, "पैंसठ": 65,
    "छियासठ": 66, "सड़सठ": 67, "अड़सठ": 68, "उनहत्तर": 69,
    "सत्तर": 70, "इकहत्तर": 71, "बहत्तर": 72, "तिहत्तर": 73,
    "चौहत्तर": 74, "पचहत्तर": 75, "छिहत्तर": 76, "सतहत्तर": 77,
    "अठहत्तर": 78, "उन्यासी": 79, "अस्सी": 80, "इक्यासी": 81,
    "बयासी": 82, "तिरासी": 83, "चौरासी": 84, "पचासी": 85,
    "छियासी": 86, "सत्तासी": 87, "अठासी": 88, "नवासी": 89,
    "नब्बे": 90, "इक्यानवे": 91, "बयानवे": 92, "तिरानवे": 93,
    "चौरानवे": 94, "पचानवे": 95, "छियानवे": 96, "सत्तानवे": 97,
    "अट्ठानवे": 98, "निन्यानवे": 99,
    # NOTE: "सौ" is a scale, not a ones entry — it must multiply, not add.
}
_HI_SCALES = {"सौ": 100, "हज़ार": 1000, "हजार": 1000, "लाख": 100_000,
              "करोड़": 10_000_000, "करोड": 10_000_000}

_EN_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fourty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90,
}
_EN_SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000,
              "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000,
              "million": 1_000_000}


def _eval_span(tokens: list[str]) -> str:
    """Evaluate a span of number words to a digit string.

    If every token is a single digit (0-9), concatenate (phone/PIN style).
    Otherwise use the standard current/total scale accumulation.
    """
    ones: dict[str, int] = {**_HI_ONES, **_EN_ONES}
    if all(tok in ones and ones[tok] <= 9 for tok in tokens):
        return "".join(str(ones[t]) for t in tokens)
    total, current = 0, 0
    for tok in tokens:
        if tok in ones:
            current += ones[tok]
        else:
            scale = _HI_SCALES.get(tok) or _EN_SCALES.get(tok) or 1
            if scale == 100:
                current = max(current, 1) * 100
            else:
                total += max(current, 1) * scale
                current = 0
    return str(total + current)


def numbers_to_digits(text: str) -> str:
    """Convert consecutive Hindi/English number-word spans to digit strings.

    Non-number tokens pass through untouched. "सात सौ पचास" -> "750",
    "five hundred" -> "500", "दो लाख चालीस हजार" -> "240000",
    "नौ आठ सात" -> "987" (digit stream).
    """
    num_words = set(_HI_ONES) | set(_HI_SCALES) | set(_EN_ONES) | set(_EN_SCALES)
    out: list[str] = []
    span: list[str] = []

    def flush() -> None:
        nonlocal span
        if span:
            out.append(_eval_span(span))
            span = []

    for tok in text.split():
        if tok in num_words:
            span.append(tok)
        else:
            flush()
            out.append(tok)
    flush()
    return " ".join(out)


def canonical(text: str | None) -> str:
    """Full canonical form: normalized text with number words as digits."""
    return numbers_to_digits(normalize_text(text))
