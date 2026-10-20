"""digits -> spoken words for Timbre read-backs.

Inverse of noiselab.normalize.numbers_to_digits: say_amount(750, 'hinglish')
-> 'saat sau pachaas'. Round-trip property is unit-tested.
"""

from __future__ import annotations

_HI = [
    "शून्य", "एक", "दो", "तीन", "चार", "पाँच", "छह", "सात", "आठ", "नौ",
    "दस", "ग्यारह", "बारह", "तेरह", "चौदह", "पंद्रह", "सोलह", "सत्रह",
    "अठारह", "उन्नीस", "बीस", "इक्कीस", "बाईस", "तेईस", "चौबीस", "पच्चीस",
    "छब्बीस", "सत्ताईस", "अट्ठाईस", "उनतीस", "तीस", "इकतीस", "बत्तीस",
    "तैंतीस", "चौंतीस", "पैंतीस", "छत्तीस", "सैंतीस", "अड़तीस", "उनतालीस",
    "चालीस", "इकतालीस", "बयालीस", "तैंतालीस", "चवालीस", "पैंतालीस",
    "छियालीस", "सैंतालीस", "अड़तालीस", "उनचास", "पचास", "इक्यावन", "बावन",
    "तिरपन", "चौवन", "पचपन", "छप्पन", "सत्तावन", "अट्ठावन", "उनसठ", "साठ",
    "इकसठ", "बासठ", "तिरसठ", "चौंसठ", "पैंसठ", "छियासठ", "सड़सठ", "अड़सठ",
    "उनहत्तर", "सत्तर", "इकहत्तर", "बहत्तर", "तिहत्तर", "चौहत्तर",
    "पचहत्तर", "छिहत्तर", "सतहत्तर", "अठहत्तर", "उन्यासी", "अस्सी",
    "इक्यासी", "बयासी", "तिरासी", "चौरासी", "पचासी", "छियासी", "सत्तासी",
    "अठासी", "नवासी", "नब्बे", "इक्यानबे", "बानबे", "तिरानबे", "चौरानबे",
    "पचानबे", "छियानबे", "सत्तानबे", "अठानबे", "निन्यानवे",
]

_ROM = [
    "zero", "ek", "do", "teen", "chaar", "paanch", "chhah", "saat", "aath",
    "nau", "das", "gyarah", "barah", "terah", "chaudah", "pandrah", "solah",
    "satrah", "atharah", "unnis", "bees", "ikkis", "bais", "teis", "chaubis",
    "pachchis", "chhabbis", "sattais", "atthais", "untis", "tees", "iktis",
    "battis", "taintis", "chauntis", "paintis", "chhattis", "saintis",
    "adtis", "untalis", "chalis", "iktalis", "bayalis", "taintalis",
    "chawalis", "paintalis", "chhiyalis", "saintalis", "adtalis", "unchas",
    "pachaas", "ikyavan", "bavan", "tirpan", "chauvan", "pachpan",
    "chhappan", "sattavan", "atthavan", "unsath", "saath", "iksath",
    "basath", "tirsath", "chaunsath", "painsath", "chhiyasath", "sadsath",
    "adsath", "unhattar", "sattar", "ikhattar", "bahattar", "tihattar",
    "chauhattar", "pachhattar", "chhihattar", "sathattar", "athhattar",
    "unyasi", "assi", "ikyasi", "bayasi", "tirasi", "chaurasi", "pachasi",
    "chhiyasi", "sattasi", "athasi", "navasi", "nabbe", "ikyanbe", "banbe",
    "tiranbe", "chauranbe", "pachanbe", "chhiyanbe", "sattanbe", "athanbe",
    "ninyanbe",
]

_SCALES_HI = [(10_000_000, "करोड़"), (100_000, "लाख"), (1000, "हज़ार"), (100, "सौ")]
_SCALES_ROM = [(10_000_000, "karod"), (100_000, "lakh"), (1000, "hazaar"),
               (100, "sau")]


def _say(n: int, table: list[str], scales: list[tuple[int, str]]) -> str:
    if n < 0:
        return "minus " + _say(-n, table, scales)
    if n < 100:
        return table[n]
    for value, word in scales:
        if n >= value:
            q, r = divmod(n, value)
            head = _say(q, table, scales) + " " + word
            return head + (" " + _say(r, table, scales) if r else "")
    raise AssertionError("unreachable")


def say_hi(n: int) -> str:
    """Devanagari spoken form: say_hi(5200) -> 'पाँच हज़ार दो सौ'."""
    return _say(n, _HI, _SCALES_HI)


def say_hinglish(n: int) -> str:
    """Romanized spoken form: say_hinglish(5200) -> 'paanch hazaar do sau'."""
    return _say(n, _ROM, _SCALES_ROM)


def say_amount(paise: int, lang: str = "hinglish") -> str:
    """Money phrase for read-backs: 75000 paise -> 'saat sau pachaas rupaye'."""
    rupees = paise // 100
    words = say_hi(rupees) if lang == "hi" else say_hinglish(rupees)
    unit = "रुपये" if lang == "hi" else "rupaye"
    return f"{words} {unit}"
