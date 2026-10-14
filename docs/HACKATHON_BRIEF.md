# Great Indian AI Internship Challenge 2026 — Research Brief

*Compiled 2026-10-14 from live sources. Facts verified where marked; uncertainties flagged.*

## Sources checked

| Source | Status |
|---|---|
| https://gnani.ai/internship | ✅ fetched (note: `www.` prefix failed; apex domain works) |
| Blog post (great-indian-ai-internship-challenge-2026) | ✅ fetched |
| https://docs.gnani.ai/llms.txt (full doc index) | ✅ fetched |
| STT REST doc | ✅ fetched |
| TTS REST doc + Voice Catalog + Text Normalization guide | ✅ fetched |
| Quick start | ✅ fetched |
| PyPI `gnani-vachana` page | ❌ fetch blocked — using installed SDK v0.8.1 as source of truth |
| HuggingFace model page | ❌ fetch blocked — URL confirmed as `huggingface.co/gnani/gnani-evon-v3.3-30B-A3B` |

## The challenge

- **What:** Gnani AI's open build challenge. Theme: **"Build Sovereign AI for India."** No set problem statement — build any working application on Gnani AI models/APIs, demo it publicly, explain how you built it.
- **Organiser:** Gnani AI (Bengaluru). Voice AI stack: Prisma (STT), Timbre (TTS), Evon (LLM, open weights), Warp (not offered to participants).
- **Rewards run in parallel:**
  - Up to **100 paid 6-month internships** starting Jan 1, 2027; stipend **up to ₹1 lakh/month** each (a *ceiling*, confirmed per person in the written offer only).
  - **10 awards × ₹50,000** (₹5 lakh total). One award max per person/team.
- **Cost:** Free. Every registrant gets **5,000 programme credits** on the API platform (app.gnani.ai/voice). Team credits go to the primary registrant.
- **Team size:** Solo or exactly 2. Each member interviewed independently; one can get an offer without the other — document who built what.
- **One entry per participant/team.** Project details editable until final submission.

## Key dates

| Milestone | Date |
|---|---|
| Contest start | Oct 1, 2026 |
| **Final submissions close** | **Nov 10, 2026, 11:59 PM IST — fixed, no extensions** |
| Build window | 41 days total |
| Interviews | After close, individual 1:1 |
| Internship start | Jan 1, 2027 |

## Eligibility (all three required on registration day)

1. Currently enrolled student in a degree/course at a college or university **in India** (BTech/MTech/BBA/MBA/BCA/MCA/BSc listed; "Other" exists).
2. **18+** on registration day.
3. Building **solo or with exactly one teammate** who also qualifies.

## Deliverables (submission)

- Working demo video of the application.
- Written explanation of the project.
- The Gnani AI models/APIs used (must name them).
- One nominated public post link per platform (LinkedIn and/or X).
- Registration form: name, email, phone, college, degree/course, discipline, year, city, solo/team.

## Selection pipeline (5 stages)

1. **Post a public demo** on LinkedIn or X with **#GreatIndianAIInternshipChallenge** and **#GnaniAI**, tag Gnani AI. *The post must be live BEFORE you submit* — tagging alone doesn't complete the entry.
2. **Engagement check** — Gnani verifies reactions/comments/reshares on nominated posts, recorded at closing cutoff.
3. **Eligibility check** — genuine use of Gnani AI tech + participation rules.
4. **Shortlisting** — eligible projects ranked by **verified engagement** → interview shortlist.
5. **Individual interviews** → written offers (stipend + terms in the offer).

⚠️ **Implication:** shortlisting is engagement-driven, so an early, polished public post matters as much as the build. Post live by Oct 30 target is correct strategy.

## The 10 awards (₹50,000 each)

| # | Award | Criteria |
|---|---|---|
| 1 | Main Character | Best build in a regional or low-resource Indian language |
| 2 | Mixed Vibes | Best code-mixed voice build (Hinglish, Tanglish, Benglish) |
| 3 | Real Deal | Most useful real-world problem (farmers, kirana, rural health…) |
| 4 | **Noise Canceller** | Best performance on messy, noisy **telephonic** audio |
| 5 | Two-Person Army | Best two-person team |
| 6 | **Solo Ninja** | Best solo participant |
| 7 | Jugaad Genius | Most creative/unexpected use |
| 8 | Small Town, Big Build | Best entry from Tier 2/3 city or college |
| 9 | Demo Day Drop | Best 60-second demo video |
| 10 | Crowd Favourite | Public votes on LinkedIn/X |

Gnani's own suggested examples (a signal of what will be **crowded**): Kannada farmer helpline (Main Character/Real Deal), **Hinglish kirana voice-ordering bot (Mixed Vibes/Real Deal)**, call summariser on noisy phone audio (Noise Canceller), Tamil voice tutor (Jugaad Genius).

## Disqualifiers / rules

- Purchased engagement, bots, paid promotion, engagement exchanges, plagiarism, **misleading demos** → disqualification. ("A demo that fakes a result will cost you more than one that shows an honest limitation.")
- **Synthetic data only.** No real phone numbers, account numbers, Aadhaar, PAN, or recordings of others without consent. Voice data = personal data under DPDP Act. Recording *yourself* is explicitly allowed.
- Must genuinely use Gnani AI models/APIs and name them.
- Agent Builder is **out of scope** — no APIs for it; credits only work on the API platform (app.gnani.ai/voice).
- No participant workspace — submission via a form emailed after registration.
- Nothing in the rules forbids using a non-Gnani LLM for reasoning, BUT the submission must "genuinely use Gnani AI technology" — safest pattern: Prisma + Timbre carry the voice pipeline, and any extra NLP is rules-based or self-hosted Evon.

## Gnani products — what's actually callable

| Product | Access | Notes |
|---|---|---|
| **Prisma v2.5 (STT)** | ✅ REST + WebSocket + Batch API | `POST https://api.vachana.ai/stt/v3`. 10 languages. ≤60 s clips (ideal ≤30 s). WAV/MP3/OGG/FLAC/AAC/M4A, server converts to 16 kHz mono. `format=verbatim` (default) or `transcribe` (ITN: ₹ amounts, dates, times, phone/PIN digit streams, Indian digit grouping). `itn_native_numerals` for native-script digits. `bias_list`/`bias_score` word boosting (≤100 words, verbatim only). `enable_substitution`+`substitution_map` (≤10 find-replace rules post-ITN). |
| **Timbre v2.5 (TTS, beta)** | ✅ REST + SSE + WebSocket | `POST https://api.vachana.ai/api/v1/tts/inference`. 42 voices, 10 Indic languages + English + **Hinglish (`hi-en`, voice Poorvi)**. Params: `language` (incl. `auto`), `speed` (0.85–1.15 or slow/medium/fast). Output: wav/raw/mp3/ogg/mulaw/alaw, 8–48 kHz. Automatic text normalization (numbers, ₹, dates, IDs). |
| **Timbre v2.0** | ⚠️ SDK default, docs say "will be deprecated soon" | Only 4 voices. **Do not use.** |
| **Voice Cloning (`vachana-vc-v1`)** | ✅ REST + SSE + WS | Embedding generation from 5–30 s reference audio, then cloned TTS. On the same platform — presumably same credits. |
| **STT Batch API** | ✅ | Async jobs for long/multiple files; 9 languages (no gu-IN/pa-IN). |
| **Evon v3.3 (LLM)** | ❌ **NOT on the API platform** — confirmed. | 30B MoE (~3.5B active), 128K ctx, 11 Indian languages, Apache 2.0. Weights by request on HF (`gnani/gnani-evon-v3.3-30B-A3B`). Running it needs real GPU hardware we don't have → treat as unavailable unless rules-level NLP suffices. |
| **Agent Builder / Warp** | ❌ out of scope |  |

### STT language codes (REST)

`bn-IN, en-IN, gu-IN, hi-IN, kn-IN, ml-IN, mr-IN, pa-IN, ta-IN, te-IN` — **10 total.**
- **No `hi-en` STT code.** For code-mixed audio: `en-IN` accepts Hindi-English mixed speech and outputs **Latin script**; `hi-IN` outputs Devanagari. This is a key finding for the corpus + normalizer design.
- Output script = the language's native script (Devanagari for hi/mr, Gurmukhi for pa, etc.). English → Latin.

### TTS `language` values (Timbre v2.5)

`auto, hi-IN, en-IN, ta-IN, te-IN, kn-IN, ml-IN, mr-IN, pa-IN, bn-IN, gu-IN, hi-en`
- **`hi-en` is valid on the server** (Hinglish → Poorvi) — but **installed SDK v0.8.1 rejects it client-side** (its `SUPPORTED_TTS_LANGUAGES` frozenset lacks `hi-en`). Workaround: `language="auto"`, or direct REST call.
- `auto` detects language from script; Latin-only text → English profile. TN guide uses bare `hi`/`en` codes in one table — the inference doc uses `hi-IN` style; use `-IN` forms (SDK validates those).
- `hinglish` (the word) is explicitly rejected; `hi-en` is the code.

### Limits & pricing

- No public per-call credit pricing found in docs. Dashboard tracks usage. We will **count every API call** and log to PROGRESS.md.
- Rate limit: `429` exists; no published numbers → build backoff in from the start.
- STT errors: 400 (bad params/format, >60 s), 403 (auth/credits), 429, 500, 503.
- TTS errors: 400 (invalid params/voice), 429, 500 (retry w/ backoff), 503.

## Corrections to what I believed

| Belief | Verdict |
|---|---|
| ~10 awards named Noise Canceller, Jugaad Genius, Mixed Vibes, Demo Day Drop, Solo Ninja, Small Town Big Build, Real Deal | ✅ Correct — plus Main Character, Two-Person Army, Crowd Favourite |
| Shortlisting driven by verified engagement on public post | ✅ Confirmed — it's stage 1–3 of the pipeline |
| 5,000 credits | ✅ |
| STT: `/stt/v3`, `X-API-Key-ID`, ≤60 s, those formats, ITN flag | ✅ — plus `bias_list`, `substitution_map`, `itn_native_numerals` |
| `timbre-v2.0` is DEPRECATED/rejected by server | ⚠️ **Partially wrong.** Docs say it "will be deprecated soon" — it may still work. SDK 0.8.1 still defaults to it. Use `timbre-v2.5` regardless. |
| Raw digits/currency mispronounce; write numbers as words | ⚠️ **Outdated.** v2.5 has automatic Text Normalization for numbers/currency/dates/IDs. Writing words is still the safer option for our benchmark (controls exactly what is spoken), but raw `₹500` now normalizes fine. Verify empirically. |
| Kaveri + hi-IN → HTTP 500 | Plausible (voice/lang mismatch). Docs now warn mismatched `language` "may reduce quality" rather than error. Keep voices matched to preferred language; use `auto` or `hi-en` for Poorvi. |
| `hi-en` rejected | ❌ **Wrong.** `hi-en` is the correct server value for Hinglish — the *installed SDK* (0.8.1) rejects it client-side. This is the 02_roundtrip.py bug. |
| Evon not on API | ✅ Confirmed. Open weights on HF by request; needs our own GPU. |
| gnani-ai/gnani HF org | ❌ Correct org is `gnani`: `huggingface.co/gnani/gnani-evon-v3.3-30B-A3B` |

## Remaining uncertainties

- Credit cost per STT/TTS call (not published) → measure from dashboard after first runs; keep a call counter.
- Exact rate limits → assume conservative; backoff on 429/5xx.
- Whether `timbre-v2.0` still responds → irrelevant, we use v2.5.
- `multi_lang_codes` param mentioned in docs (multilingual en-IN+hi-IN model) — exists in API but not in SDK 0.8.1's `transcribe()`. Could matter for Hinglish STT; test via REST if needed.
