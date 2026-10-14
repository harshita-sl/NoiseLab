"""Controlled degradation: noise mixing at exact SNRs + telephony simulation.

Noise sources:
- synthetic generators (white / pink / fan / traffic / babble) — fully
  deterministic, licence-free
- real recordings dropped into data/noise/ (any .wav/.flac/.ogg; looped or
  trimmed to fit). See data/noise/README.md.

Every function takes/returns float32 mono numpy arrays + sample rate.
Deterministic given `seed`.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np
from scipy import signal
import soundfile as sf

logger = logging.getLogger(__name__)

NOISE_DIR = Path(__file__).resolve().parent.parent / "data" / "noise"
SYNTH_NOISES = ("white", "pink", "fan", "traffic", "babble")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x)) + 1e-12))


def measured_snr(clean: np.ndarray, degraded: np.ndarray) -> float:
    """SNR of `degraded` relative to `clean` (noise = degraded - clean)."""
    noise = degraded - clean
    return 20.0 * np.log10(rms(clean) / rms(noise))


def _rng(seed: int, tag: str = "") -> np.random.Generator:
    h = int(hashlib.sha256(f"{seed}|{tag}".encode()).hexdigest()[:8], 16)
    return np.random.default_rng(h)


def list_noise_files() -> list[Path]:
    if not NOISE_DIR.exists():
        return []
    return sorted(p for p in NOISE_DIR.iterdir()
                  if p.suffix.lower() in {".wav", ".flac", ".ogg"})


def _load_noise_file(path: Path, n: int, sr: int, seed: int) -> np.ndarray:
    data, fsr = sf.read(str(path), dtype="float32", always_2d=True)
    data = data[:, 0]
    if fsr != sr:
        data = signal.resample_poly(data, sr, fsr)
    if len(data) == 0:
        raise ValueError(f"empty noise file: {path}")
    g = _rng(seed, path.name)
    if len(data) >= n:
        start = int(g.integers(0, len(data) - n + 1))
        return data[start:start + n]
    reps = int(np.ceil(n / len(data)))
    return np.tile(data, reps)[:n]


# ---------------------------------------------------------------------------
# Synthetic noise generators
# ---------------------------------------------------------------------------

def _white(n: int, g: np.random.Generator) -> np.ndarray:
    return g.standard_normal(n).astype(np.float32)


def _pink(n: int, sr: int, g: np.random.Generator) -> np.ndarray:
    """Approximate pink noise: white noise filtered by 1/sqrt(f)."""
    x = g.standard_normal(n)
    spec = np.fft.rfft(x)
    freqs = np.fft.rfftfreq(n, 1.0 / sr)
    freqs[0] = freqs[1]
    spec = spec / np.sqrt(freqs)
    y = np.fft.irfft(spec, n).astype(np.float32)
    return y / (rms(y) + 1e-12)


def _fan(n: int, sr: int, g: np.random.Generator) -> np.ndarray:
    """Fan: mains hum harmonics + steady broadband bed."""
    t = np.arange(n) / sr
    hum = np.zeros(n, dtype=np.float64)
    for k in (1, 2, 3, 4):
        hum += (0.6 ** k) * np.sin(2 * np.pi * 50 * k * t + g.uniform(0, 6.28))
    bed = signal.sosfilt(
        signal.butter(4, 400, "lowpass", fs=sr, output="sos"),
        g.standard_normal(n))
    y = hum + 0.8 * bed
    return (y / (rms(y) + 1e-12)).astype(np.float32)


def _traffic(n: int, sr: int, g: np.random.Generator) -> np.ndarray:
    """Traffic: low rumble + slow pass-by amplitude swells."""
    x = signal.sosfilt(
        signal.butter(4, 500, "lowpass", fs=sr, output="sos"),
        g.standard_normal(n))
    t = np.arange(n) / sr
    lfo = 0.55 + 0.45 * np.sin(2 * np.pi * 0.2 * t + g.uniform(0, 6.28))
    hiss = signal.sosfilt(
        signal.butter(4, [800, 4000], "bandpass", fs=sr, output="sos"),
        g.standard_normal(n))
    y = x * lfo + 0.15 * hiss
    return (y / (rms(y) + 1e-12)).astype(np.float32)


def _babble(n: int, sr: int, g: np.random.Generator) -> np.ndarray:
    """Crowd babble approximation: speech-band noise, syllabic-rate AM +
    a few wandering formant-ish resonances."""
    x = signal.sosfilt(
        signal.butter(4, [300, 3400], "bandpass", fs=sr, output="sos"),
        g.standard_normal(n))
    t = np.arange(n) / sr
    am = np.zeros(n)
    for f in (3.1, 4.3, 5.7):  # syllabic-rate modulation
        am += np.sin(2 * np.pi * f * t + g.uniform(0, 6.28))
    am = 0.6 + 0.4 * am / 3.0
    y = x * am
    return (y / (rms(y) + 1e-12)).astype(np.float32)


def make_noise(kind: str, n: int, sr: int, seed: int = 0) -> np.ndarray:
    """Return `n` samples of unit-RMS noise of the given kind.

    `kind` may be a synthetic name or the stem of a file in data/noise/
    (e.g. "kitchen" for data/noise/kitchen.wav).
    """
    g = _rng(seed, kind)
    if kind == "white":
        return _white(n, g)
    if kind == "pink":
        return _pink(n, sr, g)
    if kind == "fan":
        return _fan(n, sr, g)
    if kind == "traffic":
        return _traffic(n, sr, g)
    if kind == "babble":
        return _babble(n, sr, g)
    for p in list_noise_files():
        if p.stem == kind:
            return _load_noise_file(p, n, sr, seed)
    raise ValueError(
        f"unknown noise kind '{kind}'. synthetic: {SYNTH_NOISES}; "
        f"files: {[p.stem for p in list_noise_files()]}"
    )


# ---------------------------------------------------------------------------
# Mixing
# ---------------------------------------------------------------------------

def mix_at_snr(speech: np.ndarray, noise: np.ndarray,
               snr_db: float) -> np.ndarray:
    """Mix `noise` into `speech` at exactly `snr_db` (signal : noise RMS)."""
    if len(noise) < len(speech):
        noise = np.tile(noise, int(np.ceil(len(speech) / len(noise))))
    noise = noise[: len(speech)]
    gain = rms(speech) / (rms(noise) * (10.0 ** (snr_db / 20.0)))
    return speech + gain * noise


# ---------------------------------------------------------------------------
# Telephony simulation
# ---------------------------------------------------------------------------

def _mulaw(x: np.ndarray, mu: float = 255.0) -> np.ndarray:
    """G.711 µ-law compress -> expand round trip (8-bit quantization)."""
    x = np.clip(x, -1.0, 1.0)
    y = np.sign(x) * np.log1p(mu * np.abs(x)) / np.log1p(mu)
    q = np.round((y + 1) * 127.5) / 127.5 - 1.0
    return np.sign(q) * (np.expm1(np.log1p(mu) * np.abs(q)) / mu)


def telephony(x: np.ndarray, sr: int, *, packet_loss: float = 0.0,
              clip: bool = False, seed: int = 0) -> tuple[np.ndarray, int]:
    """Simulate a phone call: 8 kHz resample, 300-3400 Hz bandpass,
    µ-law codec, optional packet loss + clipping. Returns (audio, 8000)."""
    y = signal.resample_poly(x, 8000, sr)
    sos = signal.butter(4, [300, 3400], "bandpass", fs=8000, output="sos")
    y = signal.sosfilt(sos, y)
    peak = np.max(np.abs(y)) or 1.0
    y = _mulaw(y / peak) * peak
    if clip:
        lim = np.quantile(np.abs(y), 0.95)
        y = np.clip(y, -lim, lim)
    if packet_loss > 0:
        g = _rng(seed, "plc")
        chunk = int(0.02 * 8000)  # 20 ms frames
        for i in range(0, len(y) - chunk + 1, chunk):
            if g.random() < packet_loss:
                y[i:i + chunk] = 0.0
    return y.astype(np.float32), 8000


# ---------------------------------------------------------------------------
# Condition driver
# ---------------------------------------------------------------------------

def degrade(x: np.ndarray, sr: int, *, noise: str = "none",
            snr_db: float | None = None, phone: bool = False,
            packet_loss: float = 0.0, clip: bool = False,
            seed: int = 0) -> tuple[np.ndarray, int]:
    """Apply one degradation condition. Order: noise mix -> telephony."""
    y = x
    if noise != "none" and snr_db is not None:
        y = mix_at_snr(y, make_noise(noise, len(y), sr, seed), snr_db)
        # keep peak headroom so post-processing doesn't clip
        peak = np.max(np.abs(y))
        if peak > 0.98:
            y = y * (0.98 / peak)
    if phone:
        y, sr = telephony(y, sr, packet_loss=packet_loss, clip=clip, seed=seed)
    return y, sr
