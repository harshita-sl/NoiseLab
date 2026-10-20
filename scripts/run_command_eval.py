"""Bolta Khata command eval — the headline robustness number.

Usage:
  run_command_eval.py --dry-run           # count uncached API calls (free)
  run_command_eval.py [--limit N] [--chains none,hp+specgate+loudnorm]
                                      [--conds clean,fan_10]
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from bolta.eval_commands import (EVAL_CONDITIONS, dry_count, run,
                                 summarize)
from bolta.ledger import Ledger

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")

COMMANDS = Path("data/commands.json")
RESULTS = Path("outputs/results/command_eval.json")


def main() -> int:
    args = sys.argv[1:]
    entries = json.loads(COMMANDS.read_text(encoding="utf-8"))["entries"]
    if "--limit" in args:
        entries = entries[:int(args[args.index("--limit") + 1])]
    chains = args[args.index("--chains") + 1].split(",") \
        if "--chains" in args else ["none"]
    conds = [c for c in EVAL_CONDITIONS
             if c.name in args[args.index("--conds") + 1].split(",")] \
        if "--conds" in args else EVAL_CONDITIONS

    if "--dry-run" in args:
        print(json.dumps(dry_count(entries, conds, chains), indent=2))
        return 0

    if "--reparse" in args and RESULTS.exists():
        # transcripts stay cached — re-score is free
        RESULTS.write_text(json.dumps({"rows": []}), encoding="utf-8")

    db = Ledger("data/ledger.db")
    summary = run(entries, conds, chains, db, results_path=RESULTS)
    out = json.loads(RESULTS.read_text(encoding="utf-8"))
    out["summary"] = summary
    RESULTS.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                       encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
