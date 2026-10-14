"""Benchmark runner: corpus x condition matrix -> transcripts -> scores.

Design notes:
- Degraded audio is written to outputs/audio/<id>/<cond>.wav so every scored
  transcript is auditable and the demo app can replay without API calls.
- STT results are disk-cached by content hash + params — a rerun costs
  nothing unless the audio or params changed.
- plan() + dry_run() let us count required API calls before spending.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import soundfile as sf

from . import api
from .degrade import degrade
from .score import aggregate, score

logger = logging.getLogger(__name__)

AUDIO_DIR = Path("outputs/audio")
RESULTS_DIR = Path("outputs/results")


@dataclass(frozen=True)
class Condition:
    name: str
    noise: str = "none"
    snr_db: float | None = None
    phone: bool = False
    packet_loss: float = 0.0
    clip: bool = False


def default_conditions() -> list[Condition]:
    """The standard matrix: clean, noises x SNRs, telephony variants."""
    conds = [Condition("clean")]
    for noise in ("fan", "traffic", "babble", "white"):
        for snr in (20, 10, 5, 0):
            conds.append(Condition(f"{noise}_{snr}", noise=noise, snr_db=snr))
    conds.append(Condition("phone", phone=True))
    conds.append(Condition("phone_traffic_10", noise="traffic", snr_db=10,
                           phone=True))
    return conds


@dataclass
class Job:
    entry: dict
    cond: Condition
    meta: dict = field(default_factory=dict)


def load_corpus(path: str | Path) -> list[dict]:
    return json.loads(Path(path).read_text(encoding="utf-8"))["entries"]


def _degraded_path(entry_id: str, cond: Condition) -> Path:
    return AUDIO_DIR / entry_id / f"{cond.name}.wav"


def _ref_path(entry: dict) -> Path:
    return AUDIO_DIR / entry["id"] / "ref.wav"


def prepare_reference(entry: dict) -> Path:
    """Synthesize (or reuse cached) clean reference audio for an entry."""
    ref = _ref_path(entry)
    api.synth(entry["tts_text"], entry["voice"], entry["tts_lang"], ref)
    return ref


def plan(entries: list[dict],
         conditions: list[Condition] | None = None) -> list[Job]:
    conds = conditions or default_conditions()
    return [Job(e, c) for e in entries for c in conds]


def dry_run(jobs: list[Job]) -> dict:
    """Count the API calls a run would need (not in any cache)."""
    tts_needed, stt_needed = 0, 0
    seen_tts: set[str] = set()
    for job in jobs:
        e, c = job.entry, job.cond
        if e["id"] not in seen_tts:
            seen_tts.add(e["id"])
            if not api.synth_is_cached(e["tts_text"], e["voice"],
                                       e["tts_lang"]):
                tts_needed += 1
        wav = _degraded_path(e["id"], c)
        if wav.exists():
            if api.cache_lookup(wav, e["stt_lang"]) is None:
                stt_needed += 1
        else:
            stt_needed += 1  # wav must be rendered; STT not cached
    return {"jobs": len(jobs), "tts_calls_needed": tts_needed,
            "stt_calls_needed": stt_needed,
            "total_api_calls": tts_needed + stt_needed}


def _ensure_degraded(entry: dict, cond: Condition, ref_wav: Path) -> Path:
    out = _degraded_path(entry["id"], cond)
    if out.exists():
        return out
    x, sr = sf.read(str(ref_wav), dtype="float32", always_2d=True)
    x = x[:, 0]
    # stable seed: hash() is process-randomized, so derive from sha256
    seed = int.from_bytes(
        hashlib.sha256(f"{entry['id']}|{cond.name}".encode()).digest()[:4],
        "big")
    y, osr = degrade(x, sr, noise=cond.noise, snr_db=cond.snr_db,
                     phone=cond.phone, packet_loss=cond.packet_loss,
                     clip=cond.clip, seed=seed)
    out.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out), y, osr, subtype="PCM_16")
    return out


def run(jobs: list[Job], *, delay: float = 0.3,
        results_path: Path | None = None) -> list[dict]:
    """Execute jobs; returns scored rows. Writes results JSON incrementally
    so an interrupted run keeps its progress."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    results_path = results_path or RESULTS_DIR / "results.json"

    rows: list[dict] = []
    if results_path.exists():
        rows = json.loads(results_path.read_text(encoding="utf-8"))["rows"]
    done = {(r["id"], r["cond"]) for r in rows}

    for i, job in enumerate(jobs, 1):
        e, c = job.entry, job.cond
        if (e["id"], c.name) in done:
            continue
        try:
            ref_wav = prepare_reference(e)
            wav = _ensure_degraded(e, c, ref_wav)
            res = api.transcribe_cached(wav, e["stt_lang"])
            hyp = res.get("transcript", "")
            s = score(e["ref"], hyp, e["entities"])
            row = {"id": e["id"], "split": e["split"], "cond": c.name,
                   "stt_lang": e["stt_lang"], "hyp": hyp,
                   "score": s.to_dict()}
        except Exception as exc:  # noqa: BLE001 - record and continue
            logger.error("job %s/%s failed: %s", e["id"], c.name, exc)
            row = {"id": e["id"], "split": e["split"], "cond": c.name,
                   "stt_lang": e["stt_lang"], "hyp": None,
                   "score": None, "error": str(exc)[:300]}
        rows.append(row)
        done.add((e["id"], c.name))
        results_path.write_text(
            json.dumps({"rows": rows,
                        "aggregate": aggregate(
                            [r for r in rows if r["score"]], key="cond")},
                       ensure_ascii=False, indent=2),
            encoding="utf-8")
        logger.info("[%d/%d] %s %s -> wer=%s", i, len(jobs), e["id"], c.name,
                    row["score"]["wer"] if row["score"] else "ERR")
        time.sleep(delay)
    return rows


def render_heatmap(rows: list[dict], out_png: str | Path) -> None:
    """Mean WER heatmap over (noise x snr)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    scored = [r for r in rows if r.get("score")]
    noises, snrs = [], []
    for r in scored:
        cond = r["cond"]
        if cond == "clean":
            n, s = "clean", "clean"
        elif cond.startswith("phone"):
            n, s = cond, cond
        else:
            n, s = cond.rsplit("_", 1)
        noises.append(n)
        snrs.append(s)
    noise_axis = ["clean"] + sorted({n for n in noises if n != "clean"})
    snr_axis = [s for s in ("clean", "20", "10", "5", "0")
                if s in set(snrs) or s == "clean"]

    grid = np.full((len(noise_axis), len(snr_axis)), np.nan)
    for ni, n in enumerate(noise_axis):
        for si, s in enumerate(snr_axis):
            vals = [r["score"]["wer"] for r in scored
                    if (r["cond"] == "clean" and n == "clean" and s == "clean")
                    or (r["cond"] == f"{n}_{s}")]
            if vals:
                grid[ni, si] = sum(vals) / len(vals)

    fig, ax = plt.subplots(figsize=(7, 4.5))
    im = ax.imshow(grid, cmap="RdYlGn_r", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(len(snr_axis)), snr_axis)
    ax.set_yticks(range(len(noise_axis)), noise_axis)
    ax.set_xlabel("SNR (dB)")
    ax.set_title("Mean WER by noise x SNR")
    for ni in range(len(noise_axis)):
        for si in range(len(snr_axis)):
            if not np.isnan(grid[ni, si]):
                ax.text(si, ni, f"{grid[ni, si]:.2f}", ha="center",
                        va="center", fontsize=8)
    fig.colorbar(im, label="WER")
    fig.tight_layout()
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
