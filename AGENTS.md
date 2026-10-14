# Agent notes

- Venv: `.venv` (Python 3.10). Always call `.venv/bin/python`.
- **This shell exports a ROS `PYTHONPATH`** that leaks system packages into
  the venv and breaks pytest plugin autoloading. Run tests as:
  `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/ -q`
- Secrets: `.env` holds `GNANI_API_KEY` — gitignored, never print or commit.
- API quirks (verified Oct 2026):
  - `language="hi-en"` valid on TTS server but rejected by gnani-vachana
    0.8.1 client-side → `noiselab.api.synth` routes it via REST.
  - Full-size WAV uploads intermittently trip the edge WAF (HTTP 403) while
    identical audio as FLAC passes → `transcribe()` falls back to FLAC.
  - Intermittent connection resets — always retry with backoff.
- STT scripts: hi-IN → Devanagari; en-IN on Hinglish → Latin lowercase.
  No hi-en STT code. `format=transcribe` enables ITN.
- Benchmarks never pay twice: TTS cache `outputs/tts_cache/`, STT cache
  `outputs/stt_cache/` keyed by audio-hash + params.
