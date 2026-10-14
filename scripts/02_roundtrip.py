"""Round-trip test: TTS -> STT for a few sentences.

Bug history: this script previously only produced audio for sentence 1.
Root causes found:
  1. `gnani_helpers.py` was missing -> ModuleNotFoundError killed the script.
  2. Sentence 5 passed language="hi-en" (correct per the API docs) but the
     installed SDK (gnani-vachana 0.8.1) validates `language` client-side and
     its allowlist lacks "hi-en" -> ValueError before any request was sent.
     gnani_helpers.synth() now routes "hi-en" through direct REST.
  3. One full-size WAV upload was 403-blocked by the Cloudflare WAF while the
     same audio as FLAC passed. gnani_helpers.transcribe() retries and falls
     back to FLAC on persistent failures.
"""

import json
import logging
from pathlib import Path

from dotenv import load_dotenv

from gnani_helpers import synth, transcribe

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

out = Path("outputs")
out.mkdir(exist_ok=True)

# (spoken text, tts voice, tts language, stt language_code)
sentences = [
    ("राहुल ने आज पाँच सौ रुपये दिए।", "Nalini", "hi-IN", "hi-IN"),
    ("आज मैगी के बीस पैकेट बिक गए।", "Nalini", "hi-IN", "hi-IN"),
    ("रमेश का उधार सात सौ पचास रुपये है।", "Nalini", "hi-IN", "hi-IN"),
    ("राहुल ने 500 रुपये दिए और मैगी के 20 पैकेट बिक गए।", "Nalini", "hi-IN", "hi-IN"),
    ("Rahul ne 500 rupaye diye aur Maggi ke 20 packet bik gaye.", "Poorvi", "hi-en", "en-IN"),
]

results = []
for i, (text, voice, tts_lang, stt_lang) in enumerate(sentences, 1):
    wav = out / f"s{i:02d}.wav"
    try:
        synth(text, voice, tts_lang, wav)
        res = transcribe(wav, stt_lang)
        heard = res.get("transcript")
    except Exception as e:  # noqa: BLE001 - record and continue
        res, heard = {"error": str(e)}, None
        print(f"\nSentence {i} FAILED: {e}")
    results.append({"said": text, "heard": heard, "raw": res})
    print(f"\nSAID : {text}\nHEARD: {heard}")

(out / "first_results.json").write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
)
