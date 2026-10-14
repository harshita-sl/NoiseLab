# Gnani models / APIs used (submission write-up draft)

## APIs used

| Gnani model/API | How it's used in NoiseLab |
|---|---|
| **Prisma v2.5 (STT, REST `/stt/v3`)** | Transcribes every degraded/enhanced clip in the benchmark; verbatim + ITN (`format=transcribe`) formats compared; `language_code` per corpus entry (hi-IN / en-IN for code-mixed / mr-IN). |
| **Timbre v2.5 (TTS, REST `/api/v1/tts/inference`)** | Generates the controlled clean speech corpus — voices Nalini/Deepak (Hindi), Poorvi (Hinglish, `language=hi-en`), Zahira/Ishaan (Marathi). `audio_config`: 16 kHz PCM WAV. |

No other Gnani products used. Evon v3.3 is open-weights only (not on the API
platform) and was not required — all post-ASR logic is rules-based.

## Engineering around the API (worth mentioning in the written explanation)

- `hi-en` (Hinglish) TTS language is valid server-side but rejected by the
  gnani-vachana 0.8.1 SDK's client-side allowlist → NoiseLab calls REST
  directly for it.
- Some full-size WAV uploads intermittently trip the edge WAF (HTTP 403)
  while byte-identical audio as FLAC passes → the client layer retries then
  falls back to FLAC.
- Every call is disk-cached by content hash — reruns are free; measured
  results are reproducible.

## Honest limitations stated

- Corpus audio is Timbre-synthesized → cleaner and less varied than real
  speech; the real-world set (`data/real/`, own voice) exists to expose that
  gap, and the write-up reports both.
- Enhancement results are reported per condition including where they hurt;
  no unmeasured improvement is claimed.
