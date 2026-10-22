"""Render the headline chart: action-success % per noise condition.

Reads outputs/results/command_eval.json, writes
outputs/results/command_eval.png — grouped bars, per condition,
with per-language breakdown table printed to stdout.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

RESULTS = Path("outputs/results/command_eval.json")
OUT = Path("outputs/results/command_eval.png")

COND_ORDER = ["clean", "fan_10", "fan_5", "traffic_10", "babble_5",
              "phone"]


def main() -> int:
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = d["rows"]

    by_cond = defaultdict(list)
    by_cond_split = defaultdict(lambda: defaultdict(list))
    for r in rows:
        if r["chain"] != "none":
            continue
        by_cond[r["condition"]].append(r["action_ok"])
        by_cond_split[r["condition"]][r["split"]].append(r["action_ok"])

    conds = [c for c in COND_ORDER if c in by_cond]
    rates = [sum(by_cond[c]) / len(by_cond[c]) * 100 for c in conds]

    fig, ax = plt.subplots(figsize=(8, 4.2))
    bars = ax.bar(range(len(conds)), rates,
                  color=["#2e7d32" if c == "clean" else "#1565c0"
                         for c in conds])
    for b, v in zip(bars, rates):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.0f}%",
                ha="center", fontsize=9)
    ax.set_xticks(range(len(conds)), conds)
    ax.set_ylim(0, 105)
    ax.set_ylabel("end-to-end action success (%)")
    ax.set_title("Bolta Khata — command success vs shop noise "
                 f"(n={len(rows)} live Prisma calls)")
    ax.axhline(90, ls="--", c="grey", lw=0.8)
    fig.tight_layout()
    fig.savefig(OUT, dpi=140)
    print("wrote", OUT)

    print(f"\n{'condition':<12}", *[f'{s:>9}' for s in
                                   ['hinglish', 'hi', 'te', 'teleng']])
    for c in conds:
        line = f"{c:<12}"
        for s in ("hinglish", "hi", "te", "teleng"):
            v = by_cond_split[c].get(s)
            line += f" {sum(v)/len(v)*100:>8.0f}%" if v else f" {'—':>9}"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
