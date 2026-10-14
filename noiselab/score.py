"""Scoring: WER, CER and critical-entity accuracy.

WER/CER are computed on `canonical()` text — number words become digits and
script/spelling variants fold, so "₹500" (ITN) and "पाँच सौ" (verbatim)
score as the same value. Entity accuracy checks each marked entity value in
the corpus against the canonicalized hypothesis using word boundaries
("500" must not match inside "5000").
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

import jiwer

from .normalize import canonical


def _is_word_char(c: str) -> bool:
    # Same notion as normalize.py: letters/marks/numbers are word chars.
    return unicodedata.category(c)[0] in "LMN" or c == "_"


def entity_hit(value: str, canonical_hyp: str) -> bool:
    r"""True if entity `value` appears as a bounded token span in the hyp.

    Boundaries are category-based, not \w-based — Devanagari matras are not
    \w chars, so "राम" must not match inside "रामायण".
    """
    v = canonical(value)
    if not v:
        return False
    for m in re.finditer(re.escape(v), canonical_hyp):
        s, e = m.span()
        before = canonical_hyp[s - 1] if s > 0 else " "
        after = canonical_hyp[e] if e < len(canonical_hyp) else " "
        if not _is_word_char(before) and not _is_word_char(after):
            return True
    return False


@dataclass
class Score:
    wer: float
    cer: float
    entity_hits: int
    entity_total: int
    entity_acc: float | None
    entity_details: list[dict] = field(default_factory=list)
    ref_canonical: str = ""
    hyp_canonical: str = ""

    def to_dict(self) -> dict:
        return {
            "wer": round(self.wer, 4),
            "cer": round(self.cer, 4),
            "entity_hits": self.entity_hits,
            "entity_total": self.entity_total,
            "entity_acc": (round(self.entity_acc, 4)
                           if self.entity_acc is not None else None),
            "entity_details": self.entity_details,
            "ref_canonical": self.ref_canonical,
            "hyp_canonical": self.hyp_canonical,
        }


def score(ref: str, hyp: str | None,
          entities: list[dict] | None = None) -> Score:
    """Score one hypothesis against a reference."""
    cref = canonical(ref)
    chyp = canonical(hyp)

    if not cref:
        wer = cer = 0.0 if not chyp else 1.0
    elif not chyp:
        wer = cer = 1.0
    else:
        wer = float(jiwer.wer(cref, chyp))
        cer = float(jiwer.cer(cref, chyp))

    details = []
    hits = 0
    for ent in entities or []:
        ok = entity_hit(ent["value"], chyp)
        hits += ok
        details.append({"type": ent["type"], "value": ent["value"], "hit": ok})
    total = len(details)

    return Score(
        wer=wer,
        cer=cer,
        entity_hits=hits,
        entity_total=total,
        entity_acc=(hits / total) if total else None,
        entity_details=details,
        ref_canonical=cref,
        hyp_canonical=chyp,
    )


def aggregate(rows: list[dict], key: str | None = None) -> dict:
    """Mean WER/CER/entity-acc over scored rows (each row carries a `score`
    dict). If `key` is given, rows are grouped by row[key]."""
    def _mean(vals):
        vals = [v for v in vals if v is not None]
        return sum(vals) / len(vals) if vals else None

    def _agg(rows_):
        return {
            "n": len(rows_),
            "wer": _mean([r["score"]["wer"] for r in rows_]),
            "cer": _mean([r["score"]["cer"] for r in rows_]),
            "entity_acc": _mean([r["score"]["entity_acc"] for r in rows_]),
            "entity_hits": sum(r["score"]["entity_hits"] for r in rows_),
            "entity_total": sum(r["score"]["entity_total"] for r in rows_),
        }

    if key is None:
        return {"all": _agg(rows)}
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(str(r.get(key)), []).append(r)
    return {k: _agg(v) for k, v in sorted(groups.items())}
