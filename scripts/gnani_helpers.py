"""Shared helpers for Gnani API calls.

- synth(): cached TTS synthesis with retry/backoff. Cache keyed by
  (text, voice, language, model, sample rate) so we never pay twice.
  language="hi-en" (Hinglish) is accepted by the server but rejected by
  gnani-vachana 0.8.1 client-side validation, so it goes through REST directly.
- transcribe(): STT with retry/backoff. Full-size WAV uploads occasionally
  trip the Cloudflare WAF (403 "blocked") while the same audio as FLAC goes
  through, so on persistent 403 we fall back to FLAC bytes.
"""

from __future__ import annotations

import hashlib
import io
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

logger = logging.getLogger(__name__)

CACHE_DIR = Path("outputs/tts_cache")
RETRY_STATUSES = {403, 429, 500, 502, 503}
_tts_client: GnaniTTSClient | None = None
_stt_client: GnaniSTTClient | None = None


def _tts() -> GnaniTTSClient:
    global _tts_client
    if _tts_client is None:
        _tts_client = GnaniTTSClient()
    return _tts_client


def _stt() -> GnaniSTTClient:
    global _stt_client
    if _stt_client is None:
        _stt_client = GnaniSTTClient()
    return _stt_client


def _synth_rest(
    text: str, voice: str, language: str, model: str, sample_rate: int
) -> bytes:
    """Direct REST TTS — used for language='hi-en' which the SDK rejects."""
    resp = requests.post(
        "https://api.vachana.ai/api/v1/tts/inference",
        headers={
            "Content-Type": "application/json",
            "X-API-Key-ID": os.environ["GNANI_API_KEY"],
        },
        json={
            "text": text,
            "voice": voice,
            "model": model,
            "language": language,
            "speed": 1.0,
            "audio_config": {
                "sample_rate": sample_rate,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        },
        timeout=60,
    )
    if resp.status_code != 200:
        from gnani.tts.exceptions import APIError

        raise APIError(resp.status_code, resp.text)
    return resp.content


def synth(
    text: str,
    voice: str,
    language: str,
    out_path: str | Path,
    *,
    model: str = "timbre-v2.5",
    sample_rate: int = 16000,
    max_retries: int = 4,
) -> Path:
    """Synthesize `text` to `out_path`, using a disk cache + retry/backoff."""
    out_path = Path(out_path)
    cfg = AudioConfig(sample_rate=sample_rate, encoding="linear_pcm", container="wav")
    key = hashlib.sha256(
        f"{model}|{voice}|{language}|{sample_rate}|{text}".encode("utf-8")
    ).hexdigest()[:24]
    cache_path = CACHE_DIR / f"{key}.wav"

    if cache_path.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(cache_path.read_bytes())
        logger.info("TTS cache hit -> %s", out_path)
        return out_path

    delay = 1.0
    audio = b""
    for attempt in range(1, max_retries + 1):
        try:
            if language == "hi-en":
                audio = _synth_rest(text, voice, language, model, sample_rate)
            else:
                audio = _tts().synthesize(
                    text, voice=voice, model=model, language=language,
                    audio_config=cfg,
                )
            break
        except Exception as exc:  # noqa: BLE001
            status = getattr(exc, "status_code", None)
            retryable = status is None or status in RETRY_STATUSES
            if not retryable or attempt == max_retries:
                raise
            logger.warning(
                "TTS attempt %d/%d failed (status=%s), retrying in %.1fs",
                attempt, max_retries, status, delay,
            )
            time.sleep(delay)
            delay *= 2

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(audio)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(audio)
    logger.info("TTS synthesized -> %s (%d bytes)", out_path, len(audio))
    return out_path


def _wav_to_flac_bytes(wav_path: Path) -> bytes:
    data, sr = sf.read(str(wav_path), dtype="float32")
    buf = io.BytesIO()
    sf.write(buf, data, sr, format="FLAC")
    return buf.getvalue()


def transcribe(
    audio: str | Path,
    language_code: str,
    *,
    format: str = "verbatim",
    itn_native_numerals: bool = False,
    max_retries: int = 4,
) -> dict:
    """Transcribe with retry/backoff; on persistent 403 retry as FLAC.

    Returns the raw API response dict.
    """
    audio = Path(audio)
    delay = 2.0
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            return _stt().transcribe(
                str(audio),
                language_code=language_code,
                format=format,
                itn_native_numerals=itn_native_numerals,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            status = getattr(exc, "status_code", None)
            retryable = status is None or status in RETRY_STATUSES
            if not retryable:
                raise
            if attempt < max_retries:
                logger.warning(
                    "STT attempt %d/%d failed (status=%s), retrying in %.1fs",
                    attempt, max_retries, status, delay,
                )
                time.sleep(delay)
                delay *= 2

    # Persistent failure: if the file is a WAV, try FLAC bytes — some WAV
    # payloads trip the edge WAF while identical audio as FLAC passes.
    if audio.suffix.lower() == ".wav":
        logger.info("Retrying %s as FLAC bytes after repeated failures", audio)
        try:
            flac = _wav_to_flac_bytes(audio)
            return _stt().transcribe_bytes(
                flac,
                filename="audio.flac",
                language_code=language_code,
                format=format,
                itn_native_numerals=itn_native_numerals,
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc

    raise last_exc  # type: ignore[misc]


def wav_duration_s(path: str | Path) -> float:
    """Duration of a PCM WAV file in seconds."""
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def pcm16_to_float(path: str | Path) -> tuple[np.ndarray, int]:
    """Read a WAV file to float32 mono samples."""
    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    return data[:, 0], sr
