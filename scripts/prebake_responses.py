"""Pre-synthesize common reply phrases so the demo never waits on TTS.

Every phrase is cached by api.synth's content hash — running this once
means confirm/deny/ack/undo replies play instantly offline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

from noiselab.api import synth
from bolta.respond import (ACK_HI, ACK_ROM, ASK_HI, ASK_ROM, DENY_HI,
                           DENY_ROM, REASK_HI, REASK_ROM, UNDONE_HI,
                           UNDONE_ROM, VOICE_HI, VOICE_HINGLISH)

load_dotenv()

PHRASES = [
    (ACK_HI, *VOICE_HI), (ASK_HI, *VOICE_HI), (DENY_HI, *VOICE_HI),
    (UNDONE_HI, *VOICE_HI), (REASK_HI, *VOICE_HI),
    (ACK_ROM, *VOICE_HINGLISH), (ASK_ROM, *VOICE_HINGLISH),
    (DENY_ROM, *VOICE_HINGLISH), (UNDONE_ROM, *VOICE_HINGLISH),
    (REASK_ROM, *VOICE_HINGLISH),
]


def main() -> int:
    out = Path("outputs/prebaked")
    out.mkdir(parents=True, exist_ok=True)
    for i, (text, voice, lang) in enumerate(PHRASES):
        path = out / f"{i:02d}_{lang}_{voice}.wav"
        synth(text, voice, lang, path)
        print(f"{path.name}: {text[:50]}")
    print("done — all phrases cached")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
