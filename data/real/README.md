# data/real — real-world recordings

Record **20–30 short clips** (5–15 s each) of your own voice in real noisy
places. Only your own voice — do not record other people (challenge rules).

## How to record

Use your phone's recorder app or `arecord`:

```bash
arecord -d 10 -f cd -r 16000 outputs/raw.wav
```

Suggested settings (aim for variety):

| scene | suggestion |
|---|---|
| room with fan on | stand 1–2 m from mic |
| balcony with traffic | |
| market / canteen crowd | |
| walking outside (wind + handling noise) | |
| quiet room | baseline |
| phone-call audio | call yourself, record from speaker near another phone, or use a voice note over WhatsApp |

Say things like the corpus sentences — amounts, quantities, names ("mera
udhaar saat sau pachaas rupaye hai"). Mix Hindi, Hinglish, Marathi.

## Naming + refs

Drop files as `real01.wav` … and add an entry per clip in `refs.json`:

```json
{
  "id": "real01",
  "file": "real01.wav",
  "scene": "kitchen fan, 1m",
  "stt_lang": "hi-IN",
  "ref": "verbatim transcript of what you actually said"
}
```

Then: `.venv/bin/python scripts/score_real.py` — transcribes + scores with the
same pipeline as the synthetic benchmark.

Note for the write-up: Timbre-generated speech is cleaner than real speech —
real clips usually score worse. That's a finding, not a bug.
