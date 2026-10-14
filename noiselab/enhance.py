"""Input-side robustness layer: candidate enhancers applied before STT.

All implemented with numpy/scipy only — no fragile third-party deps.
Each function takes float32 mono audio + sr, returns same. Compose with
`enhance(x, sr, chain)` where chain is e.g. "hp+specgate+loudnorm".

Candidates:
- hp        : high-pass filter, kills mains hum/rumble below 100 Hz
- specgate  : spectral gating denoiser (stationary-noise subtraction with
              over-subtraction clamping)
- loudnorm  : normalize to a target RMS (-20 dBFS) after optional soft-clip
- vad       : energy-VAD trim of leading/trailing non-speech
- combos    : "hp+specgate", "vad+specgate+loudnorm", etc.
"""

from __future__ import annotations

import logging

import numpy as np
from scipy import signal

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Primitive enhancers
# ---------------------------------------------------------------------------

def highpass(x: np.ndarray, sr: int, cutoff: float = 100.0) -> np.ndarray:
    sos = signal.butter(4, cutoff, "highpass", fs=sr, output="sos")
    return signal.sosfilt(sos, x).astype(np.float32)


def loudnorm(x: np.ndarray, sr: int, target_rms: float = 0.1) -> np.ndarray:
    """Normalize to target RMS (~-20 dBFS). Ignores sr; kept for signature
    uniformity."""
    del sr
    r = float(np.sqrt(np.mean(np.square(x)) + 1e-12))
    if r < 1e-6:
        return x
    y = x * (target_rms / r)
    peak = np.max(np.abs(y))
    if peak > 0.98:
        y = y * (0.98 / peak)
    return y.astype(np.float32)


def vad_trim(x: np.ndarray, sr: int, *, frame_ms: float = 20.0,
             thresh_ratio: float = 2.5, pad_ms: float = 150.0) -> np.ndarray:
    """Trim leading/trailing non-speech by energy VAD.

    Threshold = thresh_ratio * median frame RMS (robust to stationary noise).
    Keeps pad_ms context around detected speech.
    """
    fl = max(1, int(frame_ms * sr / 1000))
    n_frames = len(x) // fl
    if n_frames < 3:
        return x
    frames = x[: n_frames * fl].reshape(n_frames, fl)
    energy = np.sqrt(np.mean(frames**2, axis=1))
    # Low-percentile floor: median fails when non-speech is <50% of the clip.
    floor = np.percentile(energy, 15)
    thresh = max(floor * thresh_ratio, 1e-4)
    active = energy > thresh
    if not active.any():
        return x
    first, last = int(np.argmax(active)), len(active) - int(np.argmax(active[::-1])) - 1
    pad = int(pad_ms / frame_ms)
    start = max(0, (first - pad) * fl)
    end = min(len(x), (last + pad + 1) * fl)
    return x[start:end]


def specgate(x: np.ndarray, sr: int, *, n_fft: int = 512,
             hop_ratio: float = 0.5, n_noise_frames: int = 8,
             over_sub: float = 1.2, min_gain: float = 0.05) -> np.ndarray:
    """Spectral-gating denoiser.

    Noise profile = mean magnitude spectrum of the first `n_noise_frames`
    frames (works when utterances start in noise/silence — true for our
    TTS corpus, which has a lead-in). Gain is floored at min_gain to avoid
    musical noise and speech damage.
    """
    if len(x) < n_fft * 2:
        return x
    hop = int(n_fft * hop_ratio)
    win = signal.windows.hann(n_fft)
    f, t, Z = signal.stft(x, fs=sr, window=win, nperseg=n_fft,
                          noverlap=n_fft - hop)
    mag = np.abs(Z)
    noise_mag = np.mean(mag[:, :n_noise_frames], axis=1, keepdims=True)
    gain = np.clip(1.0 - over_sub * (noise_mag / (mag + 1e-9)),
                   min_gain, 1.0)
    Z2 = Z * gain
    _, y = signal.istft(Z2, fs=sr, window=win, nperseg=n_fft,
                        noverlap=n_fft - hop)
    return y[: len(x)].astype(np.float32)


# ---------------------------------------------------------------------------
# Registry + chaining
# ---------------------------------------------------------------------------

_ENHANCERS = {
    "hp": highpass,
    "specgate": specgate,
    "loudnorm": loudnorm,
    "vad": vad_trim,
}


def available() -> list[str]:
    return list(_ENHANCERS)


def enhance(x: np.ndarray, sr: int, chain: str) -> np.ndarray:
    """Apply a '+'-separated enhancer chain. 'none'/'raw' = passthrough."""
    if chain in ("none", "raw", ""):
        return x
    y = x
    for name in chain.split("+"):
        fn = _ENHANCERS.get(name)
        if fn is None:
            raise ValueError(f"unknown enhancer '{name}'. "
                             f"available: {list(_ENHANCERS)}")
        y = fn(y, sr)
        if len(y) < 32:
            logger.warning("chain %s produced near-empty audio", chain)
            return y
    return y


CANDIDATE_CHAINS = [
    "none",
    "hp",
    "loudnorm",
    "vad",
    "specgate",
    "hp+specgate",
    "hp+specgate+loudnorm",
    "vad+hp+specgate+loudnorm",
]
