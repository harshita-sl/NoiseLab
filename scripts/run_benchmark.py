"""Benchmark CLI.

Dry-run (counts API calls, spends nothing):
    .venv/bin/python scripts/run_benchmark.py --dry-run

Run (default 20 entries):
    .venv/bin/python scripts/run_benchmark.py --limit 20

Full corpus:
    .venv/bin/python scripts/run_benchmark.py
"""

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from noiselab.runner import (dry_run, default_conditions, load_corpus, plan,
                             render_heatmap, run)
from noiselab.score import aggregate

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_benchmark")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None,
                    help="cap number of corpus entries")
    ap.add_argument("--split", choices=["hi", "hinglish", "mr"],
                    default=None, help="only this corpus split")
    ap.add_argument("--conds", default=None,
                    help="comma-separated condition names (default: all 19)")
    ap.add_argument("--dry-run", action="store_true",
                    help="count needed API calls and exit")
    ap.add_argument("--heatmap", default="outputs/results/heatmap.png")
    args = ap.parse_args()

    entries = load_corpus("data/corpus.json")
    if args.split:
        entries = [e for e in entries if e["split"] == args.split]
    if args.limit:
        entries = entries[: args.limit]

    conds = default_conditions()
    if args.conds:
        wanted = set(args.conds.split(","))
        conds = [c for c in conds if c.name in wanted]
        missing = wanted - {c.name for c in conds}
        if missing:
            logger.error("unknown conditions: %s", missing)
            return 2

    jobs = plan(entries, conds)
    est = dry_run(jobs)
    print("\n=== PLAN ===")
    print(f"entries={len(entries)} conditions={len(conds)} jobs={est['jobs']}")
    print(f"API calls needed: TTS={est['tts_calls_needed']} "
          f"STT={est['stt_calls_needed']} total={est['total_api_calls']}")

    if args.dry_run:
        print("(dry run — no API calls made)")
        return 0

    rows = run(jobs)
    scored = [r for r in rows if r.get("score")]
    agg = aggregate(scored, key="cond")
    print("\n=== AGGREGATE (mean WER / entity-acc by condition) ===")
    for cond, m in agg.items():
        ea = f"{m['entity_acc']:.2f}" if m['entity_acc'] is not None else "n/a"
        print(f"  {cond:20s} n={m['n']:3d}  wer={m['wer']:.3f}  "
              f"cer={m['cer']:.3f}  entity_acc={ea}")
    if scored:
        render_heatmap(scored, args.heatmap)
        print(f"\nheatmap -> {args.heatmap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
