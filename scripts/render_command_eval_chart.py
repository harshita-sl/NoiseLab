"""Headline chart: action-success % per noise condition, raw vs enhanced.

Reads outputs/results/command_eval.json -> command_eval.png
Grouped bars per condition for every chain present; per-language
table prints to stdout.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

RESULTS = Path("outputs/results/command_eval.json")
OUT = Path("outputs/results/command_eval.png")

COND_ORDER = ["clean", "fan_10", "fan_5", "traffic_10", "babble_5",
              "phone"]
CHAIN_LABEL = {"none": "raw (no enhancement)",
               "hp+specgate+loudnorm": "enhanced (hp+specgate+loudnorm)"}


def main() -> int:
    d = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = d["rows"]

    by = defaultdict(list)                     # (cond, chain) -> [bool]
    by_cond_split = defaultdict(lambda: defaultdict(list))
    for r in rows:
        by[(r["condition"], r["chain"])].append(r["action_ok"])
        if r["chain"] == "none":
            by_cond_split[r["condition"]][r["split"]].append(
                r["action_ok"])

    conds = [c for c in COND_ORDER if any(k[0] == c for k in by)]
    chains = sorted({k[1] for k in by},
                    key=lambda c: (c != "none", c))
    n_c = len(conds)
    width = 0.35
    xs = np.arange(n_c)

    fig, ax = plt.subplots(figsize=(8.5, 4.4))
    colors = ["#1565c0", "#43a047", "#ef6c00"]
    for ci, chain in enumerate(chains):
        vals = [sum(by[(c, chain)]) / len(by[(c, chain)]) * 100
                if by.get((c, chain)) else 0 for c in conds]
        pos = xs + (ci - (len(chains) - 1) / 2) * width
        bars = ax.bar(pos, vals, width * 0.9,
                      label=CHAIN_LABEL.get(chain, chain),
                      color=colors[ci % len(colors)])
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 1.2,
                    f"{v:.0f}", ha="center", fontsize=8)

    ax.set_xticks(xs, conds)
    ax.set_ylim(0, 108)
    ax.set_ylabel("end-to-end action success (%)")
    ax.set_title("Bolta Khata — command success vs shop noise\n"
                 "Prisma v2.5, 84 commands, live API")
    ax.legend(fontsize=8, loc="lower left")
    ax.axhline(90, ls="--", c="grey", lw=0.7)
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
