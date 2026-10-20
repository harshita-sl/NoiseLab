"""Command-level eval: does the right ACTION survive noise?

Pipeline per (command, condition, chain):
    TTS clean -> degrade(cond) -> enhance(chain) -> Prisma STT
    -> parse -> resolve -> proposal -> compare vs expected intent+slots.

Metrics: intent accuracy, slot accuracy, end-to-end action success.
Everything reuses noiselab caches; a run costs 0 on replay.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from noiselab import api
from noiselab.degrade import degrade
from noiselab.runner import Condition

from bolta.actions import propose
from bolta.ledger import Ledger
from bolta.normalize_bridge import alias_set
from bolta.parse import parse

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("outputs/audio_cmd")
RESULTS = Path("outputs/results/command_eval.json")

EVAL_CONDITIONS = [
    Condition("clean"),
    Condition("fan_10", noise="fan", snr_db=10),
    Condition("fan_5", noise="fan", snr_db=5),
    Condition("traffic_10", noise="traffic", snr_db=10),
    Condition("babble_5", noise="babble", snr_db=5),
    Condition("phone", phone=True),
]


@dataclass
class EvalRow:
    entry_id: str
    split: str
    condition: str
    chain: str
    transcript: str
    expected_intent: str
    got_intent: str
    intent_ok: bool
    slot_hits: int
    slot_total: int
    action_ok: bool
    error: str = ""

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def _ref_wav(entry: dict) -> Path:
    return AUDIO_DIR / entry["id"] / "ref.wav"


def _deg_wav(entry: dict, cond: Condition, chain: str) -> Path:
    suffix = cond.name if chain in ("none", "raw", "") \
        else f"{cond.name}__{chain.replace('+', '_')}"
    return AUDIO_DIR / entry["id"] / f"{suffix}.wav"


def prepare(entry: dict) -> Path:
    """Synthesize clean command audio (cached)."""
    ref = _ref_wav(entry)
    api.synth(entry["tts_text"], entry["voice"], entry["tts_lang"], ref)
    return ref


def render(entry: dict, cond: Condition, chain: str, ref: Path,
           seed: int = 0) -> Path:
    """Degraded (+ optionally enhanced) wav on disk."""
    out = _deg_wav(entry, cond, chain)
    if out.exists():
        return out
    x, sr = sf.read(str(ref), dtype="float32")
    x = np.asarray(x)
    if x.ndim > 1:
        x = x[:, 0]
    y, ysr = degrade(x, sr, noise=cond.noise, snr_db=cond.snr_db,
                     phone=cond.phone, seed=seed)
    if chain not in ("none", "raw", ""):
        from noiselab.enhance import enhance
        y = enhance(y, ysr, chain)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), y, ysr, subtype="PCM_16")
    return out


def _slot_ok(cmd, expected: dict, db: Ledger) -> tuple[int, int]:
    """Expected slots verified against RESOLVED ids (alias-aware)."""
    hits = total = 0
    for key, want in expected.items():
        if key == "intent":
            continue
        total += 1
        if key == "customer":
            cid = cmd.slots.get("customer_id")
            if cid is not None:
                row = db.conn.execute(
                    "SELECT * FROM customers WHERE id=?", (cid,)).fetchone()
                if row and want.lower() in alias_set(row):
                    hits += 1
        elif key == "product":
            pid = cmd.slots.get("product_id")
            if pid is not None:
                row = db.conn.execute(
                    "SELECT * FROM products WHERE id=?", (pid,)).fetchone()
                if row and want.lower() in alias_set(row):
                    hits += 1
        elif key in ("qty", "unit", "amount", "credit"):
            got = cmd.slots.get(key)
            if got == want or (isinstance(got, float) and got == float(want)):
                hits += 1
    return hits, total


def eval_one(entry: dict, cond: Condition, chain: str, db: Ledger,
             *, transcriber=api.transcribe_cached) -> EvalRow:
    wav = _deg_wav(entry, cond, chain)
    expected = entry["expected"]
    try:
        res = transcriber(wav, entry["stt_lang"])
        hyp = res.get("transcript", "")
    except Exception as exc:  # noqa: BLE001
        return EvalRow(entry["id"], entry["split"], cond.name, chain, "",
                       expected.get("intent", "?"), "", False, 0, 0,
                       False, error=str(exc)[:200])
    cmd = parse(hyp, entry["stt_lang"])
    prop = propose(cmd, db)
    intent_ok = prop.intent == expected.get("intent")
    sh, st = _slot_ok(cmd, expected, db)
    action_ok = intent_ok and not prop.error and sh == st
    if expected.get("intent") == "unknown":
        action_ok = prop.intent in ("unknown",) or bool(prop.error)
    return EvalRow(entry["id"], entry["split"], cond.name, chain, hyp,
                   expected.get("intent", "?"), prop.intent, intent_ok,
                   sh, st, action_ok)


def dry_count(commands: list[dict], conditions: list[Condition],
              chains: list[str]) -> dict:
    """Count uncached API calls a full matrix would need."""
    tts = stt = 0
    for e in commands:
        if not api.synth_is_cached(e["tts_text"], e["voice"], e["tts_lang"]):
            tts += 1
        for cond in conditions:
            for chain in chains:
                wav = _deg_wav(e, cond, chain)
                if not wav.exists() or \
                        api.cache_lookup(wav, e["stt_lang"]) is None:
                    stt += 1
    return {"commands": len(commands), "jobs": len(commands)
            * len(conditions) * len(chains),
            "tts_calls": tts, "stt_calls": stt, "total": tts + stt}


def run(commands: list[dict], conditions: list[Condition],
        chains: list[str], db: Ledger, *,
        results_path: Path = RESULTS, delay: float = 0.2) -> dict:
    """Full eval. Incremental: appends to results_path, retries errors."""
    old = json.loads(results_path.read_text(encoding="utf-8")) \
        if results_path.exists() else {"rows": []}
    rows = [r for r in old["rows"] if not r.get("error")]
    done = {(r["entry_id"], r["condition"], r["chain"]) for r in rows}
    for e in commands:
        ref = prepare(e)
        for cond in conditions:
            for chain in chains:
                if (e["id"], cond.name, chain) in done:
                    continue
                render(e, cond, chain, ref)
                row = eval_one(e, cond, chain, db)
                rows.append(row.to_dict())
                results_path.parent.mkdir(parents=True, exist_ok=True)
                results_path.write_text(json.dumps(
                    {"rows": rows}, ensure_ascii=False, indent=2),
                    encoding="utf-8")
                logger.info("%s %s %s -> %s (ok=%s)", e["id"], cond.name,
                            chain, row.got_intent, row.action_ok)
                time.sleep(delay)
    return summarize(rows)


def summarize(rows: list[dict]) -> dict:
    """intent-acc / slot-acc / action-success per condition x chain."""
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(f"{r['condition']}|{r['chain']}", []).append(r)
    agg = {}
    for k, rs in sorted(groups.items()):
        cond, chain = k.split("|")
        n = len(rs)
        agg[cond] = agg.get(cond, {})
        agg[cond][chain] = {
            "n": n,
            "intent_acc": round(sum(r["intent_ok"] for r in rs) / n, 3),
            "slot_acc": round(sum(r["slot_hits"] for r in rs)
                              / max(1, sum(r["slot_total"] for r in rs)), 3),
            "action_success": round(sum(r["action_ok"] for r in rs) / n, 3),
        }
    return {"n_rows": len(rows), "by_condition": agg}
