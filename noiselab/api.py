"""Gnani API access layer: cached TTS + resilient STT.

- synth(): disk-cached TTS keyed on (text, voice, language, model, rate).
  language="hi-en" is accepted by the server but rejected by gnani-vachana
  0.8.1's client-side validation, so it goes through REST directly.
- transcribe(): retry/backoff on transient errors and WAF blocks; on
  persistent failure of a WAV upload, retries once as FLAC bytes (identical
  audio) — full-size WAV uploads intermittently trip the edge WAF (observed
  Oct 2026).
- transcribe_cached(): transcript disk cache keyed by audio-content hash +
  request params. The benchmark never pays twice for the same audio.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import time
import wave
from pathlib import Path

import numpy as np
import requests
import soundfile as sf
from gnani.stt import GnaniSTTClient
from gnani.tts import AudioConfig, GnaniTTSClient
from gnani.tts.exceptions import APIError as TTSAPIError

logger = logging.getLogger(__name__)

RETRY_STATUSES = {403, 429, 500, 502, 503}
TTS_CACHE = Path("outputs/tts_cache")
STT_CACHE = Path("outputs/stt_cache")

_tts_client: GnaniTTSClient | None = None
_stt_client: GnaniSTTClient | None = None


def tts_client() -> GnaniTTSClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = GnaniTTSClient()
    return _tts_client


def stt_client() -> GnaniSTTClient:
    global _stt_client
    if _stt_client is None:
        _stt_client = GnaniSTTClient()
    return _stt_client


def _synth_rest(text: str, voice: str, language: str, model: str,
                sample_rate: int) -> bytes:
    """Direct REST TTS — used for language='hi-en' which the SDK rejects."""
    resp = requests.post(
        "https://api.vachana.ai/api/v1/tts/inference",
        headers={
            "Content-Type": "application/json",
            "X-API-Key-ID": os.environ["GNANI_API_KEY"],
        },
        json={
            "text": text, "voice": voice, "model": model,
            "language": language, "speed": 1.0,
            "audio_config": {"sample_rate": sample_rate,
                             "encoding": "linear_pcm", "container": "wav"},
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise TTSAPIError(resp.status_code, resp.text)
    return resp.content


def synth(text: str, voice: str, language: str, out_path: str | Path,
          *, model: str = "timbre-v2.5", sample_rate: int = 16000,
          max_retries: int = 4) -> Path:
    """Synthesize `text` to `out_path`, disk-cached + retry/backoff."""
    out_path = Path(out_path)
    key = hashlib.sha256(
        f"{model}|{voice}|{language}|{sample_rate}|{text}".encode()
    ).hexdigest()[:24]
    cache_path = TTS_CACHE / f"{key}.wav"

    if cache_path.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(cache_path.read_bytes())
        return out_path

    cfg = AudioConfig(sample_rate=sample_rate, encoding="linear_pcm",
                      container="wav")
    delay, audio = 1.0, b""
    for attempt in range(1, max_retries + 1):
        try:
            if language == "hi-en":
                audio = _synth_rest(text, voice, language, model, sample_rate)
            else:
                audio = tts_client().synthesize(
                    text, voice=voice, model=model, language=language,
                    audio_config=cfg)
            break
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            retryable = status is None or status in RETRY_STATUSES
            if not retryable or attempt == max_retries:
                raise
            logger.warning("TTS %d/%d failed (status=%s), retry in %.1fs",
                           attempt, max_retries, status, delay)
            time.sleep(delay)
            delay *= 2

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    return out_path


def _wav_to_flac_bytes(wav_path: Path) -> bytes:
    data, sr = sf.read(str(wav_path), dtype="float32")
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="FLAC")
    return buf.getvalue()


def transcribe(audio: str | Path, language_code: str, *,
               format: str = "verbatim", itn_native_numerals: bool = False,
               max_retries: int = 4) -> dict:
    """Transcribe with retry/backoff; on persistent failure of a WAV,
    retries once as FLAC bytes."""
    audio = Path(audio)
    delay, last_exc = 2.0, None
    kwargs = dict(language_code=language_code, format=format,
                  itn_native_numerals=itn_native_numerals)

    for attempt in range(1, max_retries + 1):
        try:
            return stt_client().transcribe(str(audio), **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            status = getattr(exc, "status_code", None)
            retryable = status is None or status in RETRY_STATUSES
            if not retryable:
                raise
            if attempt < max_retries:
                logger.warning("STT %d/%d failed (status=%s), retry in %.1fs",
                               attempt, max_retries, status, delay)
                time.sleep(delay)
                delay *= 2

    if audio.suffix.lower() == ".wav":
        logger.info("Retrying %s as FLAC bytes after repeated failures", audio)
        try:
            return stt_client().transcribe_bytes(
                _wav_to_flac_bytes(audio), filename="audio.flac", **kwargs)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    raise last_exc  # type: ignore[misc]


def audio_hash(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()[:24]


def transcribe_cached(audio: str | Path, language_code: str, *,
                      format: str = "verbatim",
                      itn_native_numerals: bool = False,
                      cache_dir: Path = STT_CACHE,
                      force: bool = False) -> dict:
    """transcribe() with a disk cache keyed on audio bytes + params."""
    key = hashlib.sha256(
        f"{audio_hash(audio)}|{language_code}|{format}|"
        f"{int(itn_native_numerals)}".encode()
    ).hexdigest()[:32]
    cache_path = cache_dir / f"{key}.json"
    if cache_path.exists() and not force:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    res = transcribe(audio, language_code, format=format,
                     itn_native_numerals=itn_native_numerals)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(res, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    return res


def cache_lookup(audio: str | Path, language_code: str, *,
                 format: str = "verbatim",
                 itn_native_numerals: bool = False,
                 cache_dir: Path = STT_CACHE) -> dict | None:
    """Return cached transcript without calling the API (dry-run support)."""
    key = hashlib.sha256(
        f"{audio_hash(audio)}|{language_code}|{format}|"
        f"{int(itn_native_numerals)}".encode()
    ).hexdigest()[:32]
    p = cache_dir / f"{key}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def wav_duration_s(path: str | Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


MAX_STT_SECONDS = 30.0  # server-enforced (MAX_AUDIO_DURATION_EXCEEDED)


def split_at_quiet_points(x: np.ndarray, sr: int, *, max_s: float = 28.0,
                          frame_ms: float = 20.0) -> list[tuple[int, int]]:
    """Sample bounds so each chunk is <= max_s, cut at the quietest frame
    in a window before each deadline (avoids chopping mid-word)."""
    n = len(x)
    limit = int(max_s * sr)
    if n <= limit:
        return [(0, n)]
    flen = max(1, int(sr * frame_ms / 1000))
    frames = np.array([np.sqrt(np.mean(x[i:i + flen] ** 2))
                       for i in range(0, n - flen + 1, flen)])
    bounds, start = [], 0
    while n - start > limit:
        deadline = start + limit
        f_hi = min(deadline // flen, len(frames))
        f_lo = max((start + limit // 2) // flen, f_hi - int(5 * sr) // flen)
        cut = (f_lo + int(np.argmin(frames[f_lo:f_hi]))) * flen \
            if f_hi > f_lo else deadline
        bounds.append((start, cut))
        start = cut
    bounds.append((start, n))
    return bounds


def transcribe_long(audio: str | Path, language_code: str, *,
                    max_s: float = 28.0, format: str = "verbatim",
                    itn_native_numerals: bool = False,
                    tmp_dir: Path = Path("outputs/chunks")) -> dict:
    """Transcribe audio longer than the 30s API cap.

    Splits at low-energy points so each chunk fits the cap, transcribes each
    chunk through the normal cache, and joins transcripts. Short audio goes
    straight through transcribe_cached().
    """
    x, sr = sf.read(str(audio))
    bounds = split_at_quiet_points(x, sr, max_s=max_s)
    if len(bounds) == 1:
        return transcribe_cached(
            audio, language_code, format=format,
            itn_native_numerals=itn_native_numerals)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    ahash = audio_hash(audio)[:8]
    texts = []
    for i, (a, b) in enumerate(bounds):
        chunk = tmp_dir / f"{Path(audio).stem}_{ahash}_{i}.wav"
        if not chunk.exists():
            sf.write(str(chunk), x[a:b], sr)
        res = transcribe_cached(chunk, language_code, format=format,
                                itn_native_numerals=itn_native_numerals)
        texts.append(res.get("transcript", ""))
    return {"transcript": " ".join(
        t.strip() for t in texts if t).strip(), "chunks": len(bounds)}


def synth_is_cached(text: str, voice: str, language: str,
                    *, model: str = "timbre-v2.5",
                    sample_rate: int = 16000,
                    cache_dir: Path = TTS_CACHE) -> bool:
    key = hashlib.sha256(
        f"{model}|{voice}|{language}|{sample_rate}|{text}".encode()
    ).hexdigest()[:24]
    return (cache_dir / f"{key}.wav").exists()
