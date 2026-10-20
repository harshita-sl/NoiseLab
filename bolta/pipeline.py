"""The NoiseLab ↔ Bolta seam.

listen(): wav -> (optional enhance) -> transcribe_long -> transcript.
command(): transcript -> parse -> resolve -> ActionProposal.
Both sides stay independently testable: pipeline accepts injected
transcribers for offline tests/replay.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from noiselab.api import transcribe_long
from noiselab.enhance import enhance

from bolta.actions import ActionProposal, propose
from bolta.ledger import Ledger
from bolta.parse import Command, parse


def listen(wav: str | Path, lang: str, *,
           chain: str = "none",
           transcriber=transcribe_long) -> dict:
    """Audio file -> transcript dict. Enhances first if chain != none."""
    wav = Path(wav)
    if chain not in ("none", "raw", ""):
        x, sr = sf.read(str(wav), dtype="float32")
        x = np.asarray(x)
        if x.ndim > 1:
            x = x[:, 0]
        y = enhance(x, sr, chain)
        enh = wav.with_name(wav.stem + f"__{chain.replace('+', '_')}.wav")
        sf.write(str(enh), y, sr, subtype="PCM_16")
        wav = enh
    return transcriber(wav, lang)


def command(transcript: str, db: Ledger, *, lang: str = "") -> Command:
    return parse(transcript, lang)


def propose_command(transcript: str, db: Ledger, *,
                    lang: str = "") -> ActionProposal:
    return propose(parse(transcript, lang), db)


def full_turn(wav: str | Path, lang: str, db: Ledger, *,
              chain: str = "none",
              transcriber=transcribe_long) -> tuple[dict, ActionProposal]:
    """wav -> transcript -> proposal (nothing written; confirm first)."""
    res = listen(wav, lang, chain=chain, transcriber=transcriber)
    prop = propose_command(res.get("transcript", ""), db, lang=lang)
    return res, prop
