"""Evaluate enhancer chains on degraded audio: raw vs enhanced per condition.

Reads the matrix audio produced by run_benchmark (outputs/audio/<id>/<cond>.wav),
applies each candidate chain, transcribes (disk-cached), scores, and writes
outputs/results/enhance_results.json + a comparison table.

Usage:
    .venv/bin/python scripts/run_enhance_eval.py --limit 20 \
        --conds fan_5,traffic_0,phone --chains none,specgate,hp+specgate+loudnorm
    .venv/bin/python scripts/run_enhance_eval.py --dry-run --limit 20
"""

import argparse
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import soundfile as sf
from dotenv import load_dotenv

from noiselab import api
from noiselab.enhance import CANDIDATE_CHAINS, enhance
from noiselab.runner import AUDIO_DIR, RESULTS_DIR, load_corpus
from noiselab.score import aggregate, score

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_enhance_eval")


def enhanced_path(entry_id: str, cond: str, chain: str) -> Path:
    return AUDIO_DIR / entry_id / "enhanced" / f"{cond}__{chain.replace('+','-')}.wav"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--split", choices=["hi", "hinglish", "mr"], default=None)
    ap.add_argument("--conds", default=None, help="comma list; default = all "
                    "conditions with degraded audio on disk")
    ap.add_argument("--chains", default=",".join(CANDIDATE_CHAINS))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    entries = load_corpus("data/corpus.json")
    if args.split:
        entries = [e for e in entries if e["split"] == args.split]
    if args.limit:
        entries = entries[: args.limit]
    chains = [c.strip() for c in args.chains.split(",") if c.strip()]

    # available degraded conditions per entry
    work = []
    for e in entries:
        d = AUDIO_DIR / e["id"]
        if not d.exists():
            continue
        conds = sorted(p.stem for p in d.glob("*.wav") if p.stem != "ref")
        if args.conds:
            want = set(args.conds.split(","))
            conds = [c for c in conds if c in want]
        for c in conds:
            for ch in chains:
                if ch != "none":
                    work.append((e, c, ch))

    # dry-run: count uncached STT calls (enhanced wavs must exist to hash;
    # estimate = all work minus existing enhanced-cache hits)
    need = 0
    for e, c, ch in work:
        ep = enhanced_path(e["id"], c, ch)
        if ep.exists() and api.cache_lookup(ep, e["stt_lang"]) is not None:
            continue
        need += 1
    print(f"entries={len(entries)} enhanced jobs={len(work)} "
          f"STT calls needed≈{need}")
    if args.dry_run:
        return 0

    rows = []
    out = RESULTS_DIR / "enhance_results.json"
    if out.exists():
        rows = json.loads(out.read_text(encoding="utf-8"))["rows"]
    done = {(r["id"], r["cond"], r["chain"]) for r in rows}

    for i, (e, c, ch) in enumerate(work, 1):
        if (e["id"], c, ch) in done:
            continue
        try:
            x, sr = sf.read(str(AUDIO_DIR / e["id"] / f"{c}.wav"),
                            dtype="float32", always_2d=True)
            y = enhance(x[:, 0], sr, ch)
            ep = enhanced_path(e["id"], c, ch)
            ep.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(ep), y, sr, subtype="PCM_16")
            res = api.transcribe_cached(ep, e["stt_lang"])
            hyp = res.get("transcript", "")
            s = score(e["ref"], hyp, e["entities"])
            row = {"id": e["id"], "split": e["split"], "cond": c,
                   "chain": ch, "hyp": hyp, "score": s.to_dict()}
        except Exception as exc:  # noqa: BLE001
            logger.error("%s %s %s failed: %s", e["id"], c, ch, exc)
            row = {"id": e["id"], "cond": c, "chain": ch,
                   "error": str(exc)[:200], "score": None}
        rows.append(row)
        done.add((e["id"], c, ch))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"rows": rows}, ensure_ascii=False,
                                  indent=2), encoding="utf-8")
        logger.info("[%d/%d] %s %s %s wer=%s", i, len(work), e["id"], c, ch,
                    row["score"]["wer"] if row.get("score") else "ERR")

    # comparison: per (cond, chain) means, vs raw baseline from results.json
    scored = [r for r in rows if r.get("score")]
    by = {}
    for r in scored:
        by.setdefault((r["cond"], r["chain"]), []).append(r)
    print("\n=== ENHANCED: mean WER / entity-acc by cond x chain ===")
    for (cond, ch), rs in sorted(by.items()):
        m = aggregate(rs)["all"]
        ea = f"{m['entity_acc']:.2f}" if m["entity_acc"] is not None else "n/a"
        print(f"  {cond:16s} {ch:28s} n={m['n']:3d} wer={m['wer']:.3f} "
              f"ear={ea}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
