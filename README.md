# NoiseLab

How badly does real-world noise break speech-to-text — and how much can
input-side preprocessing fix it?

NoiseLab benchmarks **Gnani Prisma v2.5** (STT) on controlled degradations of
**Timbre v2.5** (TTS)-generated speech — noise types, SNR levels, telephony
simulation, Hindi / Hinglish / regional languages — then measures how much a
local robustness layer (denoising, filtering, loudness normalization, VAD
trimming) recovers. Built for the
[Great Indian AI Internship Challenge 2026](docs/HACKATHON_BRIEF.md).

## Status

Early build — see [docs/PROGRESS.md](docs/PROGRESS.md) for what's done.

## Layout

```
noiselab/     reusable package (normalize, degrade, score, enhance, ...)
scripts/    probes + pipeline entry points
data/       corpus.json, noise/, real/
tests/      pytest unit tests
outputs/    generated audio + results (gitignored)
docs/       hackathon brief, progress log, idea recommendation
```

## Setup

```bash
python3.10 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # put your GNANI_API_KEY in .env (never commit it)
```

## Tests

```bash
env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    .venv/bin/python -m pytest tests/ -q
```

(the env prefix guards against ROS's PYTHONPATH leaking system packages.)

## Key API findings (verified live, Oct 2026)

- `hi-IN` STT → Devanagari verbatim; `en-IN` on Hinglish audio → Latin
  lowercase. No `hi-en` STT code.
- `format=transcribe` enables ITN (`पाँच सौ रुपये` → `₹500`);
  `itn_native_numerals` → `₹५,०००`. Response also returns `output.literal`.
- TTS `language="hi-en"` (Hinglish/Poorvi) is valid on the server but rejected
  by gnani-vachana 0.8.1 client-side — `scripts/gnani_helpers.py` routes it
  via REST.
- Some WAV uploads trip the Cloudflare WAF (403) while the same audio as FLAC
  passes — `transcribe()` retries then falls back to FLAC.
