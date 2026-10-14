# Great Indian AI Internship Challenge 2026: Brief

Researched on **2026-10-14** from the live pages below. "Verified" means I read it on an official
page today. "Uncertain" means the sources disagree or don't say. The programme terms let Gnani change
rules, timelines and prizes at any time, so re-check https://www.gnani.ai/internship before submitting.

Sources: gnani.ai/internship, the registration page (participation terms), the launch blog
(2026-10-01), docs.gnani.ai (STT REST, Batch, Realtime, TTS REST, voices, text normalization,
Python SDK), PyPI `gnani-vachana` 0.8.1, the SDK source code, and HF `gnani-ai/gnani` and
`gnani/gnani-evon-v3.3-30B-A3B`.

## 1. The challenge in one paragraph
This is an open-brief build challenge for students in India. Build **any working application on
Gnani AI's models/APIs**, post a public demo video on LinkedIn and/or X, then submit. The theme is
"Build Sovereign AI for India". Rewards:
- Up to **100 paid 6-month internships** starting Jan 1, 2027. The stipend is **up to** ₹1 lakh/month
  per intern. That is a ceiling, not a guarantee.
- **10 awards of ₹50,000** each, judged separately from internship selection.

## 2. Dates
| Milestone | Date |
|---|---|
| Contest / build window opens | Oct 1, 2026 |
| Personal (non-institutional) email sign-in | "second week of October" |
| **Final submission (fixed, no extensions)** | **Nov 10, 2026, 11:59 PM IST** |
| Interviews | After close, shortlisted people only |
| Internship start | Jan 1, 2027 (confirmed in the written offer) |

Your plan of build-ready Oct 29, post live Oct 30, submit Nov 8 fits. Posting early matters more
than you assumed, because **engagement on the post decides the internship shortlist** (section 5).

## 3. Eligibility
- Currently enrolled at a college or university **in India**.
- **18+** on the day you register.
- Solo, or a team of exactly 2. You are solo, so you're eligible for **Solo Ninja**, not Two-Person Army.
- One entry per participant or team.

## 4. Deliverables
1. A **working application** that uses at least one Gnani model or API, shown working in a public video.
2. A public post on **LinkedIn and/or X** that:
   - explains what you built and which Gnani tech it uses,
   - **tags Gnani AI's official account**,
   - includes **#GnaniAI** and **#GreatIndianAIInternshipChallenge**.

   The post must be **live before you submit**. Nominate one post per platform.
3. A submission form (sent to your email) containing:
   - the demo video,
   - a written project explanation,
   - the Gnani models/APIs used,
   - each member's contribution,
   - the post link(s).
4. Project details can be edited until you submit. Fields: title, problem, users, models, contributions.

## 5. Selection process (verified)
1. **Engagement check.** Gnani verifies reactions, comments and reshares on your nominated posts,
   counted up to the closing cutoff.
2. **Eligibility check.** The entry must show genuine use of Gnani tech.
3. **Shortlisting.** Among eligible projects, those with the "strongest verified engagement" are
   shortlisted. This happens at project level.
4. **Individual interviews.**
5. **Written offer.** Depends on skills, interview performance and role fit.

Implications for you:
- **The internship shortlist is effectively an engagement contest.** Your technical quality only
  starts to count at the interview.
- So post as early as possible (Oct 30 is good), make the video easy to share, and write the post
  so it invites comments, for example "record a clip in your city's noise and tell me what Prisma got".
- **Never** buy engagement or join engagement-swap groups. The terms list this as disqualifying.

## 6. Awards: corrected list (10 × ₹50,000, max one per person/team)
Your list was missing three: **Main Character**, **Two-Person Army** and **Crowd Favourite**.

| # | Award | Official criterion | Fit for NoiseLab |
|---|---|---|---|
| 1 | Main Character | Best build in a regional or low-resource Indian language | Medium, if the regional language is a first-class citizen |
| 2 | Mixed Vibes | Best code-mixed voice experience (Hinglish, Tanglish, Benglish) | High (Hinglish track) |
| 3 | Real Deal | Most useful real-world problem solved (farmers, kirana, rural health) | Depends on the app built on top (Part C) |
| 4 | **Noise Canceller** | "Performs best on messy, noisy, **real telephonic** audio" | **Primary target.** It stresses *telephony* and *real* audio, so the 8 kHz/codec simulation and the real-recorded set are essential, not optional |
| 5 | Two-Person Army | Best team of two | Not eligible (solo) |
| 6 | **Solo Ninja** | Best project by a single participant | Eligible by default. A good fallback |
| 7 | Jugaad Genius | Most creative or unexpected use of the models | Possible: using Timbre to stress-test Prisma is an unusual use |
| 8 | Small Town, Big Build | Best entry from a Tier 2/3 town or college | Only if your college/city qualifies. Gnani hasn't published how this is verified |
| 9 | Demo Day Drop | Best **60-second** demo video | Applies to everyone. Plan the video early |
| 10 | Crowd Favourite | Public votes on LinkedIn/X with both hashtags | Same engagement as the shortlist |

There is no published scoring rubric for the awards beyond these one-liners. **Uncertain:** whether
you pick a category or judges assign one. The site says "pick the category your project fits best
and build toward it", but the submission form fields aren't public.

## 7. Rules and disqualification risks
- **Allowed:** genuine use of Gnani tech, named in the submission. "Your project uses Gnani AI technology."
- **Disqualifying (if substantiated):** purchased engagement, bots, paid promotion, engagement
  exchanges, plagiarism, and **misleading demos**. The blog says "A demo that fakes a result will cost
  you more than one that shows an honest limitation". That fits NoiseLab's measure-honestly approach.
- **Data/privacy:** synthetic data only. No real phone numbers, account numbers, Aadhaar, PAN or
  recorded calls of others. Recording yourself (or a consenting teammate) is explicitly allowed.
  Voice counts as personal data under the DPDP Act.
- **Other LLMs or third-party models:** **not prohibited by any rule I found.** The rules require
  that Gnani tech be used and named. They don't say "only Gnani".
  - Risk: the theme is *sovereign AI*, and the eligibility check looks for "genuine use of Gnani AI
    technology". A project whose core intelligence is GPT or Claude, with Prisma as a thin wrapper,
    could look weak.
  - Gnani's own docs (Call Analytics use case) show Prisma + Claude/OpenAI, which suggests mixing
    is acceptable.
  - Recommendation: keep Prisma/Timbre central, prefer rules or Evon for intent extraction, and
    disclose any other model openly. Confirm on the Discord.
- **IP/ownership:** governed by the programme terms ("read them before you submit"). The public
  terms text doesn't spell out IP. **Uncertain:** ask on the Discord before using code you plan to
  commercialise.
- **Agent Builder is out of scope.** The challenge covers only the API platform (app.gnani.ai/voice).

## 8. Credits
- **5,000 programme credits** per registration. Teams: the primary registrant holds them.
- **Uncertain, not public:** how many credits one STT second or one TTS character costs. Pricing
  isn't on gnani.ai/pricing (it's a sales form) or in the docs. The dashboard at app.gnani.ai/voice
  "shows usage against your credits".
  - Action: run one short TTS call and one STT call, then read the dashboard delta. NoiseLab's
    budget estimator uses that measured rate (`NOISELAB_CREDITS_PER_*` in config) rather than guessing.
- Batch STT docs say billing is **per audio duration**, and that enabling `with_denoise` does not
  change billing. Substitution docs say "billing records carry the raw transcript".
- Failed requests: no documented policy. Treat each attempt as potentially billable. NoiseLab
  caches every successful response so it never pays twice.

## 9. Which Gnani products you can actually use
| Product | What it is | On the API platform with your credits? |
|---|---|---|
| **Prisma v2.5** (STT) | REST (≤60 s), Realtime WebSocket, Batch jobs | **Yes** |
| **Timbre v2.5** (TTS, beta) | REST, SSE, WebSocket; 42 voices | **Yes** |
| Voice cloning (`vachana-vc-v1`) | Embeddings + cloned TTS | Documented on the same API. **Uncertain** whether programme credits cover it. Not needed for NoiseLab |
| **Evon v3.3** (LLM) | 30B MoE (~3.5B active), 128K context, 11 Indic languages, Apache-2.0 | **No, open weights only** (verified in the FAQ). The HF repo `gnani/gnani-evon-v3.3-30B-A3B` currently shows `gated: false` although Gnani's pages say "by request". It needs a big GPU (~60 GB in bf16), which is not realistic on a laptop. A 4-bit quant may fit ~20 GB VRAM. **Uncertain** that ready quants exist |
| Agent Builder | Console voice agents | **Out of scope** |
| "Warp" | Listed on the models page | No public API docs. Ignore |

Marketing pages say Prisma covers "40+ languages" and Timbre "21+". **The API docs list 10**
(bn, en, gu, hi, kn, ml, mr, pa, ta, te). Trust the API docs.

## 10. Prisma STT: verified technical facts
- `POST https://api.vachana.ai/stt/v3`, multipart. Header `X-API-Key-ID`. **Verified.**
- Fields:
  - `audio_file`, `language_code` (required, one of the 10 codes above).
  - `format`: `verbatim` (default) or `transcribe` (= **ITN on**).
  - `itn_native_numerals` (`₹५,०००` vs `₹5,000`).
  - `enable_substitution` + `substitution_map` (≤10 find/replace rules, applied after ITN).
  - **`bias_list` + `bias_score`** (word boosting, ≤100 single letter-only words, score in
    {0, 0.5, 1, 1.5, 2}). An **invalid list is silently ignored** and still returns 200.
- **Your belief "optional ITN flag" is slightly off.** There is no boolean. ITN is `format=transcribe`.
- Duration: ≤60 s (ideal ≤30 s). The embedded OpenAPI text says "Maximum duration: 30 seconds" in
  one place. **Keep clips ≤30 s to be safe.**
- Formats: WAV, MP3, OGG, FLAC, AAC, M4A. **Server resamples everything to 16 kHz mono.**
  - The docs don't state the "8–44.1 kHz" range for REST. That range comes from the Realtime
    socket, which accepts 8000/16000/44100/48000.
  - Implication: an 8 kHz telephony clip is upsampled server-side, so the 4 kHz bandwidth loss is real.
- Output script: native script per language (Hindi → Devanagari). `en-IN` "accepts English-Hindi
  mixed audio and generates output in English (Latin script)". So **Hinglish audio comes back in
  Devanagari under `hi-IN` and in Roman under `en-IN`.** This is the main reason the normalizer matters.
- ITN behaviour (documented): Indian digit grouping (`5,20,000`), `₹500`, `20 जनवरी 2025`,
  `सुबह 05:00`, 10-digit phone numbers compacted. Idioms like "दो तीन" are left as words.
- A multi-language REST option (`multi_lang_codes`, en-IN + hi-IN only) is mentioned in the docs
  but **not exposed in SDK 0.8.1**, and its exact syntax isn't documented on the REST page. **Uncertain.**
- Errors: 400, 403 (also "no credits"), 429 rate limit, 500 transient, 503. **No numeric rate
  limit is published.**
- **Batch STT** has a server-side **`with_denoise`** option. This is important for NoiseLab: it's
  Gnani's own enhancer and the **baseline our robustness layer must beat or match**. Batch has no
  ITN and doesn't support gu/pa, but it does support language ID among up to 3 codes.

## 11. Timbre TTS: verified technical facts
- `POST https://api.vachana.ai/api/v1/tts/inference`, JSON body. `model` must be `timbre-v2.5`.
  - The API's enum contains only `timbre-v2.5`.
  - **SDK 0.8.1 still has `DEFAULT_MODEL = "timbre-v2.0"`**, and the SDK docs confirm omitting
    `model` returns 400. **Verified.**
- `language`: `auto`, the 10 `xx-IN` codes, or **`hi-en` (Hinglish)** per the REST docs.
  - **But the SDK's `SUPPORTED_TTS_LANGUAGES` does not include `hi-en`.** `client.synthesize(...,
    language="hi-en")` raises `ValueError` *locally, before any request*.
  - The text-normalization page also says `hinglish` is not a valid value and that code-mixed text
    should use `auto`.
  - **This is the prime suspect for the round-trip bug** (section 13).
- Voices: 42, each with a preferred language. Hindi has 13 (Nalini, Bhavna, Yashvi, Urmila, Jwala,
  Chitra, Ambuja, Deepak, Roopesh, Vikrant, Hemraj, Jalaj, Omkar). English has 6 (Kaveri, Trupti,
  Devika, Pranav, Shlok, Girish). Hinglish has 1 (Poorvi). Tamil has 5 (Asmita, Trisha, Brinda,
  Vedika, Noopur). Telugu has 5. kn/ml/mr/bn/gu/pa have 2 each.
  - **Note:** your `01_hello_tts.py` uses `voice="Asmita"`, which is a **Tamil** voice, with
    `hi-IN`. Use Nalini/Deepak for Hindi.
- `speed` 0.85–1.15. Output: wav/raw/mp3/ogg/mulaw/alaw at 8–48 kHz. `mulaw`/`alaw` force 8 kHz.
  This gives NoiseLab a *server-side* G.711 telephony variant for free.
- Numbers: **the docs contradict each other.**
  - The REST page says "pass numbers as spoken words to avoid mispronunciations".
  - The newer Text Normalization guide says raw numbers, currency, dates and IDs "are now handled
    automatically", with details like lakh grouping and digit-by-digit IDs.
  - Your observation (digits mispronounced) may predate the TN update, or come from the wrong
    voice/language pair.
  - NoiseLab keeps **spoken-form text for synthesis**. It's deterministic and makes the reference
    unambiguous. Re-test raw digits once with credits to see if TN now handles them.
- "Kaveri + hi-IN gave HTTP 500": consistent with the docs ("mismatched language may reduce
  quality"). I can't verify the 500 without a key. Always pair voices with their preferred language.

## 12. Python SDK `gnani-vachana` (verified from source, v0.8.1, released 2026-10-06)
- `pip install gnani-vachana`, imported as `gnani`. Needs Python ≥3.9 (docs say 3.10+; PyPI says 3.9).
  Reads `GNANI_API_KEY` from the environment.
- `GnaniSTTClient().transcribe(path_or_bytes, language_code="hi-IN", format="verbatim"|"transcribe",
  itn_native_numerals=False)`. There is **no `bias_list`/`substitution` parameter in the SDK**.
  NoiseLab uses raw `requests` for those.
- The docs claim the SDK "handles retries automatically". **The 0.8.1 source contains no retry
  logic.** NoiseLab implements its own retry/backoff on 429/5xx.
- `GnaniTTSClient.supported_voices(model="timbre-v2.5")` returns the 42 voices. The default
  `model` argument of `supported_voices` is also `timbre-v2.0`, which returns only 4 voices.

## 13. Your beliefs: verified, corrected, uncertain
| Your belief | Status |
|---|---|
| Shortlisting driven by verified engagement on a public post | **Verified** |
| ~10 awards with the names you listed | **Corrected:** 10 awards. Missing Main Character, Two-Person Army, Crowd Favourite. Max one per entry |
| Deliverables: demo, written explanation, models/APIs used, public post | **Verified.** Also each member's contribution, the post must be live *before* submitting, and you must tag Gnani's account |
| 5,000 programme credits | **Verified.** Credit cost per call **unknown/unpublished** |
| STT: endpoint, header, ≤60 s, formats | **Verified** (keep ≤30 s; one spec line says 30) |
| STT 8–44.1 kHz | **Partly.** REST resamples any rate to 16 kHz. Rate limits are from the Realtime API |
| Optional ITN flag | **Corrected:** `format=transcribe` |
| SDK `GnaniSTTClient().transcribe(path, language_code=...)` | **Verified** |
| `timbre-v2.0` deprecated and rejected; SDK defaults to it | **Verified** (docs + SDK source) |
| Use `timbre-v2.5` + `language` | **Verified** |
| Nalini/Deepak Hindi, Kaveri English, Poorvi Hinglish, 42 voices | **Verified** |
| Raw digits mispronounce, so write numbers as words | **Contested:** the newer TN guide says digits are handled. Keep words for the benchmark, re-test once |
| Kaveri + hi-IN gave 500 | Plausible (mismatch). Not re-tested (no key on VM) |
| Evon is open weights, not on the API | **Verified** (FAQ). The HF repo currently isn't gated |
| Round-trip bug | **Likely cause:** `language="hi-en"` (or `"hinglish"`) is rejected by the SDK with a local `ValueError`, or the deprecated default model. See `docs/PROGRESS.md` once I can see your script |

## 14. Open questions to ask on the Gnani Discord
1. Credits per STT second / TTS character, and whether failed calls are billed.
2. Whether using a non-Gnani LLM (for intent extraction) is acceptable, and whether it affects award eligibility.
3. How "Small Town, Big Build" eligibility is verified.
4. The REST rate limit (requests/min) for programme keys.
5. The exact `multi_lang_codes` syntax for REST.
