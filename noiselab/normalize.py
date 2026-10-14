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

# Marathi number words distinct from Hindi ones (shared tokens like वीस,
# तीस, साठ, बारा, तेरा, चौदा, हजार, लाख are already in the tables above).
_MR_ONES = {
    "दोन": 2, "वीस": 20, "पाच": 5, "सहा": 6, "नऊ": 9, "दहा": 10, "अकरा": 11,
    "पंधरा": 15, "सोळा": 16, "सतरा": 17, "अठरा": 18, "एकोणीस": 19,
    "चाळीस": 40, "पन्नास": 50, "ऐंशी": 80, "नव्वद": 90,
    "दोनशे": 200, "तीनशे": 300, "चारशे": 400, "पाचशे": 500,
    "सहाशे": 600, "सातशे": 700, "आठशे": 800, "नऊशे": 900,
    "एकशे": 100, "पंधराशे": 1500, "एकोणचाळीस": 39,
}
_MR_SCALES = {"शंभर": 100, "हजार": 1000, "लाख": 100_000, "कोटी": 10_000_000}

# Romanized Hindi number words — en-IN STT writes code-mixed speech in Latin
# script ("paanch sau rupaye"). Common English function-word collisions are
# avoided ("so", "to"); "do" is included because "do hazaar/sau" is a frequent
# amount phrase in this domain (both ref and hyp canonicalize identically).
_ROM_HI_ONES = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "paach": 5, "cheh": 6,
    "chhah": 6, "saat": 7, "aath": 8, "ath": 8, "nau": 9, "das": 10,
    "gyarah": 11, "barah": 12, "terah": 13, "chaudah": 14, "pandrah": 15,
    "solah": 16, "satrah": 17, "atharah": 18, "unnis": 19, "bees": 20,
    "ikkis": 21, "bais": 22, "teis": 23, "chaubis": 24, "pachis": 25,
    "chhabbis": 26, "sattais": 27, "atthais": 28, "untis": 29, "tees": 30,
    "iktees": 31, "battees": 32, "taintees": 33, "chauntees": 34,
    "paintees": 35, "chhatees": 36, "saintees": 37, "adtees": 38,
    "untalees": 39, "chalees": 40, "iktalees": 41, "bayalees": 42,
    "taintalees": 43, "chawalees": 44, "paintalees": 45, "chhiyalees": 46,
    "saintalees": 47, "adtalees": 48, "unchas": 49, "pachaas": 50,
    "ikyavan": 51, "bavan": 52, "tirpan": 53, "chauvan": 54, "pachpan": 55,
    "chhappan": 56, "sattavan": 57, "atthavan": 58, "unsath": 59,
    "saath": 60, "iksath": 61, "basath": 62, "tirsath": 63,
    "chaunsath": 64, "painsath": 65, "chhiyasath": 66, "sadsath": 67,
    "adsath": 68, "unhattar": 69, "sattar": 70, "ikhattar": 71,
    "bahattar": 72, "tihattar": 73, "chauhattar": 74, "pachhattar": 75,
    "chihattar": 76, "sathattar": 77, "athattar": 78, "unyasi": 79,
    "assi": 80, "ikyasi": 81, "bayasi": 82, "tirasi": 83, "chaurasi": 84,
    "pachasi": 85, "chhiyasi": 86, "sattasi": 87, "athasi": 88,
    "nawasi": 89, "nabbe": 90, "ikyanave": 91, "bayanave": 92,
    "tiranave": 93, "chauranave": 94, "pachanave": 95, "chhiyanave": 96,
    "sattanave": 97, "atthanave": 98, "ninyanave": 99,
}
_ROM_HI_SCALES = {"sau": 100, "sow": 100, "hazaar": 1000, "hazar": 1000,
                  "karod": 10_000_000}

# Telugu — own script (te-IN STT output). Plural scale forms included
# (వందలు, వేలు). Compound hundreds like "ఐదు వందలు" -> 5 x 100.
_TE_ONES = {
    "శూన్య": 0, "ఒకటి": 1, "ఒక": 1, "రెండు": 2, "మూడు": 3, "నాలుగు": 4,
    "ఐదు": 5, "ఆరు": 6, "ఏడు": 7, "ఎనిమిది": 8, "తొమ్మిది": 9,
    "పది": 10, "పదకొండు": 11, "పన్నెండు": 12, "పదమూడు": 13,
    "పద్నాలుగు": 14, "పదిహేను": 15, "పదహారు": 16, "పదిహేడు": 17,
    "పద్దెనిమిది": 18, "పందొమ్మిది": 19, "ఇరవై": 20, "ఇరవయ్యి": 20,
    "మూప్పై": 30, "నలభై": 40, "యాభై": 50, "అరవై": 60, "డెబ్బై": 70,
    "ఎనభై": 80, "తొంభై": 90,
}
_TE_SCALES = {"వంద": 100, "వందలు": 100, "వందల": 100,
              "వేయి": 1000, "వేలు": 1000, "వేయలు": 1000, "వేల": 1000,
              "లక్ష": 100_000, "లక్షలు": 100_000, "లక్షల": 100_000,
              "కోటి": 10_000_000, "కోట్లు": 10_000_000, "కోట్ల": 10_000_000}

# Romanized Telugu — for Telenglish refs / en-IN output on te-EN audio.
_ROM_TE_ONES = {
    "okati": 1, "okka": 1, "rendu": 2, "moodu": 3, "mudu": 3,
    "naalugu": 4, "nalugu": 4, "nalgu": 4, "aidu": 5, "ayidu": 5,
    "aaru": 6, "edu": 7, "yedu": 7, "enimidi": 8, "enmidi": 8,
    "tommidi": 9, "padi": 10, "iravai": 20, "iruvai": 20, "muppai": 30,
    "nalabhai": 40, "nalubai": 40, "yabhai": 50, "yabai": 50,
    "aravai": 60, "debbai": 70, "enabhai": 80, "thombai": 90,
}
_ROM_TE_SCALES = {"vanda": 100, "vandalu": 100, "vandala": 100,
                  "veyi": 1000, "velu": 1000, "veyalu": 1000, "vel": 1000,
                  "laksha": 100_000, "lakshala": 100_000,
                  "koti": 10_000_000, "kotla": 10_000_000}

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


def _eval_span(tokens: list[str], ones: dict[str, int],
               scales: dict[str, int]) -> str:
    """Evaluate a span of number words to a digit string.

    If every token is a single digit (0-9), concatenate (phone/PIN style).
    Otherwise use the standard current/total scale accumulation.
    """
    if all(tok in ones and ones[tok] <= 9 for tok in tokens):
        return "".join(str(ones[t]) for t in tokens)
    total, current = 0, 0
    for tok in tokens:
        if tok in ones:
            current += ones[tok]
        else:
            scale = scales.get(tok, 1)
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
    ones: dict[str, int] = {**_HI_ONES, **_MR_ONES, **_EN_ONES,
                            **_ROM_HI_ONES, **_TE_ONES, **_ROM_TE_ONES}
    scales: dict[str, int] = {**_HI_SCALES, **_MR_SCALES, **_EN_SCALES,
                              **_ROM_HI_SCALES, **_TE_SCALES,
                              **_ROM_TE_SCALES}
    num_words = set(ones) | set(scales)
    out: list[str] = []
    span: list[str] = []

    def flush() -> None:
        nonlocal span
        if span:
            out.append(_eval_span(span, ones, scales))
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
