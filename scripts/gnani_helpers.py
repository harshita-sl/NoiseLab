"""Compat shim — implementation moved to noiselab.api."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from noiselab.api import (  # noqa: E402,F401
    audio_hash,
    cache_lookup,
    synth,
    transcribe,
    transcribe_cached,
    wav_duration_s,
)


def pcm16_to_float(path):  # noqa: D103 - kept for old scripts
    import soundfile as sf
    import numpy as np
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return np.asarray(data[:, 0]), sr
