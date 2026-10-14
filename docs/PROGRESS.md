# NoiseLab — Progress Log

## 2026-10-14
- Part A done: `docs/HACKATHON_BRIEF.md` written from live sources.
- **Round-trip bug FIXED.** Root causes: (a) `scripts/gnani_helpers.py` missing →
  script died at import; (b) `language="hi-en"` is valid per docs but SDK 0.8.1
  rejects it client-side → now routed via direct REST; (c) intermittent
  Cloudflare WAF 403s on full-size WAV uploads → `transcribe()` retries then
  falls back to FLAC. All 5 sentences round-trip clean now.
- Verified live: hi-IN → Devanagari verbatim; en-IN → Latin lowercase for
  Hinglish audio; ITN (`format=transcribe`) gives `₹500` / `₹५,०००` and also
  returns `output.literal` (raw verbatim) in the same response.
- `noiselab/normalize.py` + 27 unit tests passing (script cleanup, Devanagari
  digits, spelling variants, number-words→digits hi+en incl. lakh/crore).
- Env note: this shell has ROS `PYTHONPATH` — run tests as
  `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/ -q`

### API calls so far (approx)
TTS: ~8 | STT: ~20  → well under 1% of 5,000 credits (cost/call unknown, monitor on dashboard)
