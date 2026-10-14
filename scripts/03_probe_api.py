"""Probe Prisma/Timbre behaviours we need for the benchmark design.

1. Retry the Cloudflare-blocked s04 transcription.
2. ITN on/off on a Hindi amount sentence.
3. Hinglish audio (s05) transcribed as hi-IN vs en-IN (script difference).
4. Direct REST TTS with language="hi-en" (SDK 0.8.1 rejects it client-side;
   docs say the server accepts it).
"""

import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from gnani.stt import GnaniSTTClient

load_dotenv()
stt = GnaniSTTClient()
out = Path("outputs")


def transcribe_retry(path, lang, **kw):
    for attempt in range(3):
        try:
            return stt.transcribe(str(path), language_code=lang, **kw)
        except Exception as e:
            print(f"  attempt {attempt + 1} failed: {e}")
            time.sleep(2 * (attempt + 1))
    return {"error": "all retries failed"}


print("=== 1. s04 retry (hi-IN verbatim) ===")
r = transcribe_retry(out / "s04.wav", "hi-IN")
print(json.dumps(r, ensure_ascii=False))

print("\n=== 2. s01 ITN ===")
r = transcribe_retry(out / "s01.wav", "hi-IN", format="transcribe")
print("ITN:", json.dumps(r, ensure_ascii=False))
r = transcribe_retry(out / "s01.wav", "hi-IN", format="transcribe", itn_native_numerals=True)
print("ITN+native:", json.dumps(r, ensure_ascii=False))

print("\n=== 3. s05 (Hinglish audio) as hi-IN vs en-IN ===")
r = transcribe_retry(out / "s05.wav", "hi-IN")
print("hi-IN:", json.dumps(r, ensure_ascii=False))
r = transcribe_retry(out / "s05.wav", "en-IN")
print("en-IN:", json.dumps(r, ensure_ascii=False))

print("\n=== 4. Direct REST TTS with language=hi-en ===")
resp = requests.post(
    "https://api.vachana.ai/api/v1/tts/inference",
    headers={
        "Content-Type": "application/json",
        "X-API-Key-ID": os.environ["GNANI_API_KEY"],
    },
    json={
        "text": "Rahul ne paanch sau rupaye diye",
        "voice": "Poorvi",
        "model": "timbre-v2.5",
        "language": "hi-en",
        "speed": 1.0,
        "audio_config": {"sample_rate": 16000, "encoding": "linear_pcm", "container": "wav"},
    },
    timeout=60,
)
print("status:", resp.status_code, "| bytes:", len(resp.content) if resp.ok else resp.text[:200])
if resp.ok:
    (out / "hinglish_rest.wav").write_bytes(resp.content)
