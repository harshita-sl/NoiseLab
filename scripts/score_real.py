"""Score self-recorded real clips from data/real/ with the same pipeline.

Refs live in data/real/refs.json. Entities are optional (empty list ok) —
WER/CER always computed.
"""

import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from noiselab.api import transcribe_cached
from noiselab.normalize import strip_annotations
from noiselab.score import aggregate, score

load_dotenv()
logging.basicConfig(level=logging.INFO,
                    format="%(levelname)s %(name)s: %(message)s")

REAL = Path("data/real")
OUT = Path("outputs/results/real_results.json")


def main() -> int:
    refs = json.loads((REAL / "refs.json").read_text(encoding="utf-8"))["entries"]
    if not refs:
        print("no entries in data/real/refs.json — see data/real/README.md")
        return 0
    rows = []
    for e in refs:
        wav = REAL / e["file"]
        if not wav.exists():
            print(f"missing file: {wav}")
            continue
        try:
            res = transcribe_cached(wav, e["stt_lang"])
            hyp = res.get("transcript", "")
            ref = strip_annotations(e["ref"])
            s = score(ref, hyp, e.get("entities", []))
            rows.append({"id": e["id"], "scene": e.get("scene", ""),
                         "stt_lang": e["stt_lang"], "hyp": hyp,
                         "score": s.to_dict()})
            print(f"{e['id']} ({e.get('scene','')}) wer={s.wer:.2f} "
                  f"ear={s.entity_acc if s.entity_acc is not None else 'n/a'}\n"
                  f"  ref : {ref}\n  hyp : {hyp}")
        except Exception as exc:  # noqa: BLE001
            print(f"{e['id']} FAILED: {exc}")
            rows.append({"id": e["id"], "error": str(exc)[:200]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(
        {"rows": rows,
         "aggregate": aggregate([r for r in rows if r.get("score")],
                                key="scene")},
        ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
