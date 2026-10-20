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

## 2026-10-14 (cont.)
- Corpus: data/corpus.json — 52 entries (20 hi, 16 hinglish, 16 mr), entities
  marked. Chose Marathi as the regional language (Devanagari → normalizer
  extends cheaply; award-relevant regional language).
- noiselab/degrade.py: exact-SNR mixing + synth noise (white/pink/fan/
  traffic/babble) + file loading + telephony sim (8k/bandpass/mu-law/PLC).
- noiselab/score.py: WER/CER on canonical text + entity accuracy (bounded
  substring — Indic marks handled, "500" won't match "5000").
- noiselab/runner.py + scripts/run_benchmark.py: --dry-run counts calls first
  (20 entries × 19 conds = 380 jobs ≈ 398 API calls).
- noiselab/enhance.py: hp / specgate / loudnorm / vad chains + eval script.
- app.py (Streamlit): live + replay + results pages; verified boot.
- data/real/ + data/noise/ scaffolding with license log.
- IDEA_RECOMMENDATION.md written (Part C).
- **BLOCKER**: api.vachana.ai currently unreachable from this machine (conn
  resets; google/github/cloudflare.com fine → host-specific). Benchmark run
  pending connectivity. If it persists >30 min, restart the router (new IP).

### State at pause
- Everything except live benchmark runs is built + tested (61 tests green).
- `outputs/api_watch.log` polls vachana every 60s for recovery.
- Next when API is back: `scripts/run_benchmark.py --limit 20` →
  `scripts/run_enhance_eval.py` → heatmap → real clips → demo video.
- Local commits unpushed (push when ready).
- Corpus + normalizer now cover Telugu (te-IN, Telugu script refs) and
  Telenglish (Latin-script Telugu-English, scored with en-IN). Real-clip
  README updated so recordings in te/teleng plug into the same scorer.
- CORRECTION (verified Oct 19): STT server cap is 30s, not 60s as docs say —
  api returns MAX_AUDIO_DURATION_EXCEEDED. api.py now has transcribe_long():
  quiet-point split + per-chunk cached STT + transcript join.
- First real clips scored: real01 traffic/hi WER 0.00 EAR 1.0,
  real02 fan/hi WER 0.02 EAR 1.0, real03 canteen/hinglish WER 0.09 EAR 1.0.
- Normalizer learned a real variant: Prisma renders पचास as "pachas".

## Oct 20 — Bolta Khata implementation (megaplan approved)

Done: full `bolta/` package — SQLite ledger + audit/undo, synthetic
seed (18 products / 12 customers / 90-day history), rules-only parser
(Devanagari + Hinglish + Telugu script + Telenglish), fuzzy entity
resolution, action proposals, reorder math, spoken-number layer
(`say.py`), response templates, NoiseLab pipeline seam. 179 tests
green. Command eval corpus (80 commands), eval script with dry-run
(560 calls = 11.2% → needs approval). Smoke eval on live API: 3/3
correct. Streamlit app `bolta_app.py` (Counter/Khata/Stock/Replay).

Next: full command-eval run (await approval), demo hardening,
recording more real clips, submission docs.

Credits: ~30 spent total so far (smoke eval + debug calls).
