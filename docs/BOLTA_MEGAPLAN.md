# Bolta Khata — Megaplan

*Voice bookkeeping, stock, and udhaar for kirana shops — on Gnani Prisma + Timbre, with NoiseLab's measured noise-robustness as the headline. Written Oct 19, 2026. PLAN ONLY — no code until approved.*

## Executive summary (10 lines)

1. **What:** a voice-native ledger + stock + udhaar assistant for Hindi/Hinglish/Telugu-speaking shopkeepers. Speak a command → Prisma transcribes → deterministic parser extracts intent+entities → confirm card → Timbre reads it back → write lands only on "haan". Undo always available.
2. **Why it wins:** every kirana-bot competitor will demo clean audio; we demo end-to-end command success **measured** across fan/traffic/crowd/telephony at controlled SNRs — the "Noise Canceller" award made literal.
3. **Stack:** new `bolta/` package importing `noiselab/` (api, degrade, enhance, normalize, score). SQLite ledger. Streamlit UI (`bolta_app.py`), offline replay mode.
4. **No LLM.** Rules-only parsing (verified: rules don't forbid an external LLM, but rules-only is zero-risk, zero-cost, deterministic). A `parse()` seam keeps an adapter possible but unused.
5. **Decisions locked:** name = **Bolta Khata** (ledger, not ordering bot); regional commands = **Telugu**; generic corpus benchmark skipped — the Bolta command-eval is the headline result.
6. **Credit plan:** ~620 calls total (~12% of 5,000), biggest single run ~420 calls — I'll ask before firing it.
7. **Timeline:** code Oct 19–25 → **feature freeze Oct 26** → packaging Oct 29 → **public post Oct 30** → submission ≤ Nov 8.
8. **Your jobs:** record ~10 more real clips, check dashboard credits, verify parse fixes on your transcripts, record the demo, write the post.
9. **Honesty rule:** every number in the demo comes from `results.json` — WER, entity accuracy, action-success rate, including conditions where enhancement hurts.
10. **Fallback spine:** replay mode + canned audio means the 60-s demo works even if api.vachana.ai is down (it was, for 3 days last week).

---

## 1. Verified facts vs assumptions vs open questions

**Verified (live, this repo):**
- Prisma: `/stt/v3`, `X-API-Key-ID`, **30 s hard cap** (server-enforced), hi-IN→Devanagari, en-IN→Latin for code-mixed audio, ITN via `format=transcribe`, `bias_list`/`substitution_map` exist.
- Timbre v2.5: 42 voices, `hi-en`+Poorvi valid on server but SDK 0.8.1 rejects → `noiselab.api.synth` routes it via REST. Automatic TN means digits don't strictly need pre-spelling — but spoken-form control is still safer for eval.
- `transcribe_long()` handles >30 s audio (quiet-point split + cache). Everything caches to disk; re-runs are free.
- Rules: non-Gnani LLM **not forbidden**, but "must genuinely use Gnani AI tech" — rules-only removes the question entirely (HACKATHON_BRIEF.md §rules).
- Scored real clips: traffic WER 0.00, fan 0.02, canteen-Hinglish 0.09 — all EAR 1.0.
- **Credits used so far: ~11 cached calls** (5 STT + 6 TTS) + ~30 debug attempts ≈ **<1% of 5,000.**

**Assumptions:**
- ~1 credit per API call (no public pricing; will refine once you read the dashboard).
- en-IN remains the right `stt_lang` for Hinglish commands (real03 supports this).
- Timbre synthesis of command audio is "clean" input — the write-up states this vs real speech.

**Open questions:**
- Exact credit cost per call → **you check app.gnani.ai/voice dashboard** and tell me the number.
- Whether `multi_lang_codes` STT param helps Hinglish — test later only if en-IN underperforms on your clips.

**Mismatch note vs your prompt:** Timbre v2.0 is "deprecating soon," not dead (SDK still defaults to it — we use v2.5). Raw digits are now normalized by v2.5's TN, so the spoken-words converter is for *control*, not necessity.

---

## 2. Architecture

### File tree (new — nothing in `noiselab/` changes)

```
bolta/
  __init__.py
  pipeline.py      # listen() → Command: the NoiseLab ↔ Bolta seam
  parse.py         # intent grammar + entity extraction (rules-only)
  resolve.py       # fuzzy customer/product matching vs DB catalog
  actions.py       # ActionProposal dataclass + confidence + confirm state
  ledger.py        # SQLite: products/customers/txns/audit + undo
  seed.py          # synthetic catalog + 90-day sales history generator
  reorder.py       # reorder suggestions (deterministic math)
  respond.py       # reply templates hi/hinglish + confirm phrasing
  say.py           # digits → spoken Hindi/Hinglish words for TTS
  eval_commands.py # command-corpus eval: intent/slot/action accuracy
bolta_app.py       # Streamlit UI (separate; app.py stays NoiseLab's)
data/commands.json # ~80 commands: hi + hinglish + te + teleng
scripts/seed_ledger.py
scripts/run_command_eval.py
tests/test_parse.py test_resolve.py test_ledger.py test_reorder.py
      test_say.py test_e2e.py
```

### Data flow

```
[mic/upload]──►tmp.wav──►(noisy-shop toggle: noiselab.degrade)──►
noiselab.enhance(chain)──►noiselab.api.transcribe_long (cached)──►
noiselab.normalize.canonical──►bolta.parse   ─┐
      Command{intent, slots, confidence} ◄────┘
        │
        ▼
bolta.resolve (catalog fuzzy match)──►bolta.actions.propose
        │
        ▼
 CONFIRM CARD (UI) ──► user: haan/nahi
        │ haan
        ▼
ledger.write() + audit row ──►bolta.respond template ──►say.py digits→words
        │                                        │
        ▼                                        ▼
   LEDGER VIEW                    noiselab.api.synth (cached)──►🔊 read-back
        │
   UNDO button ──► audit pops last op, reverse txn written
```

### Interface contract (buildable against stubs)

```python
# noiselab side (already exists — Bolta depends on it, not vice versa)
def listen(wav: Path, lang: str, chain: str = "none") -> dict   # {transcript, cached}
    # thin wrapper: enhance() -> transcribe_long()

# bolta side
@dataclass
class Command:
    intent: str            # record_sale | record_payment | check_credit |
                           # check_stock | add_purchase | reorder_suggestion |
                           # undo | confirm | deny | unknown
    slots: dict            # customer?, product?, qty?, unit?, amount?
    confidence: float      # 0..1 — drives confirm vs re-ask
    raw: str               # canonical transcript
    unresolved: list[str]  # entity mentions with no catalog match

def parse_command(canonical_text: str, lang: str) -> Command
def resolve(cmd: Command, db: Ledger) -> Command          # fills ids / ambiguity
def propose(cmd: Command, db: Ledger) -> ActionProposal   # human desc + ops
def confirm(prop_id: int, accept: bool, db: Ledger) -> Receipt
def undo(db: Ledger) -> Receipt
```

Fixtures: `tests/fixtures/transcripts.jsonl` — canned `(audio_hash → transcript)` so the whole app + e2e tests run with zero API calls (same trick replay mode uses).

---

## 3. Data model (SQLite, `data/ledger.db`)

```sql
products(id, name_en, name_hi, aliases TEXT,  -- 'Maggi', 'मैगी', 'maggi,meegi'
         unit, pack_size INT, stock REAL, reorder_point REAL)
customers(id, name, aliases TEXT, phone NULL)  -- synthetic names only
transactions(id, ts, kind,                    -- sale|purchase|payment|credit_sale
             customer_id NULL, product_id NULL,
             qty REAL, unit, amount_paise INT,  -- integer paise, no floats
             note, source TEXT,                 -- 'voice'|'seed'|'undo'
             status TEXT DEFAULT 'ok',
             audio_hash TEXT, transcript TEXT)  -- provenance per row
audit_log(id, ts, action TEXT, txn_id NULL,     -- write|undo|confirm|deny
          payload TEXT)                          -- JSON before/after
```

Undo = write a compensating txn referencing the original (`source='undo'`), never delete. `customers.outstanding` is a computed view: Σcredit_sale − Σpayment. **Seed data:** ~25 kirana products (Maggi, atta, daal, Coke, chini, tel, biscuit…) + ~12 synthetic customers (Rahul, Sunita, Ramesh, Lakshmi, Kaka, Akka…) + 90 days of sales history per product from a seeded `numpy` Generator (weekday seasonality + occasional spikes), so reorder suggestions have real inputs.

---

## 4. Intent & entity schema

| Intent | Trigger patterns (canonicalized) | Required slots |
|---|---|---|
| `record_sale` | "<prod> <qty> <unit> (bika/biki/sold/diya)" | product, qty |
| `record_payment` | "<name> ne <amt> (diya/diye/jama kiya/paid)" | customer, amount |
| `check_credit` | "<name> ka (udhaar/baki/balance) (kitna)" | customer |
| `check_stock` | "<prod> (kitna/kitni) (bacha/bachi/hai)" | product |
| `add_purchase` | "<qty> <unit> <prod> (mangaya/aaya/order kiya)" | product, qty |
| `reorder_suggestion` | "kya order (karu/karna chahiye/mangau)" | — |
| `undo` | "undo/piche/wapas/last (entry) (hatao/cancel)" | — |
| `confirm`/`deny` | "haan/sahi/theek" / "nahi/galat/cancel" | — |
| `unknown` | everything else → honest "samajh nahi aaya" | — |

**Entity extraction order** (order matters — greedy): amount (`<num> rupaye/₹` or bare number near payment verbs) → quantity (`<num> <unit>`; units: kilo, gram, liter, packet, carton, dabba, dozen, piece + Devanagari/Telugu equivalents) → product (longest catalog alias match) → customer (remaining proper-noun candidate via catalog fuzzy match, difflib ratio ≥ 0.75). Numbers come free: `canonical()` already turns पाँच सौ/five hundred/aidu vandalu/నూటా → digits.

**Variants:** grammar tables hold Devanagari, romanized, and Telugu-script forms of the same lemma (`diya|diye|దియ్యా`…). Script doesn't matter post-`canonical()` except vocabulary — we keep per-language pattern lists.

**Disambiguation:** two candidates within Δratio < 0.10 → `confidence` drops below threshold → confirm card shows *options*, not a guessed answer ("Rahul S ya Rahul M?"). Unknown name → `unresolved[]` → card asks "naya customer banau?" — never silently creates or guesses.

---

## 5. Reorder recommendation (deterministic — formulas)

```
daily_rate[p]   = units_sold[p, last N days] / N            (N = 14, seeded data)
days_left[p]    = stock[p] / daily_rate[p]
reorder_if      = days_left[p] < lead_time[p] + safety_days[p]   (lead=2, safety=3)
suggested_qty   = ceil((daily_rate × (lead+safety) − stock) / pack_size) × pack_size
```

Output: sorted list (urgency = days_left asc) → spoken summary "Maggi 2 din mein khatam — 24 packet order karo." All math pure-python + unit-tested against hand-computed fixtures. No LLM anywhere in the loop; Timbre only voices the result.

---

## 6. Voice response layer (`respond.py` + `say.py`)

- **Templates** keyed `(lang, intent, event)` for `hi` (Devanagari, TTS `hi-IN`/Nalini) and `hinglish` (Latin, TTS `hi-en`/Poorvi — cached via the REST path):
  - confirm_prompt: *"{name}, {amt_spoken} rupaye jama — ab {bal_spoken} baaki. Sahi hai?"*
  - done: *"Likha gaya."* / unknown: *"Samajh nahi aaya — dobara bolo."*
- **`say.py`** — inverse of the normalizer: int → spoken words (`5200` → "bavan sau"/"पाँच हज़ार दो सौ"). Unit-tested round-trip: `numbers_to_digits(say(n)) == str(n)` for 0–9,99,999.
- **Phrase cache:** the ~15 most common replies are pre-synthesized at build time (`scripts/prebake_responses.py`) so the demo never waits on TTS.

---

## 7. Noise-robustness eval (the headline result)

`data/commands.json` — **~80 commands**: 32 Hinglish, 24 Hindi-Devanagari, 16 Telugu, 8 Telenglish; every intent ≥ 4×, every entity type covered. `run_command_eval.py`:

1. Timbre-synthesize clean refs (reuses `runner.prepare_reference` + cache).
2. Degrade via `degrade(x, sr, noise, snr_db, phone)` over a reduced matrix: `clean, fan_10, fan_5, traffic_10, babble_5, phone` = 6 conditions (credit-aware subset of the 19).
3. Per condition × enhancer chain (`none` vs the 1–2 best from earlier evals): `listen() → parse → resolve → propose` and compare vs expected `{intent, slots}`.
4. **Metrics:** intent accuracy, per-slot accuracy, and **end-to-end action-success** (would the right write have been proposed?) vs noise × SNR × chain → `outputs/results/command_eval.json` + heatmap via existing `render_heatmap`.
5. **Your real clips** get spoken-command entries in `data/real/refs.json` — same scorer, real-world column.

Budget: 80 TTS + 80×6 STT ≈ **560 calls**, or trimmed 60×6 = **420** — I'll dry-run count and ask before firing (>10% rule).

---

## 8. UI (`bolta_app.py`, Streamlit — reuse, don't reinvent)

- **Counter page (hero):** mic/upload → transcript → parsed Command card → **confirm card** (accept/deny/pick-option) → Timbre read-back 🔊 → ledger updates inline. "Noisy shop" toggle: `degrade(phone=True)` or `fan_10` on your live mic audio — *the demo moment*.
- **Khata page:** transactions table + per-customer udhaar balances + undo button.
- **Stock page:** levels, days-left bars, reorder list.
- **Replay page:** canned command audio + cached transcripts (zero API) — the demo's safety net.
- Keep NoiseLab's `app.py` untouched; Bolta gets its own file so both stories stay clean.

---

## 9. Testing strategy

- **Unit:** parse tables per intent × 3 scripts; `say()` round-trip; resolve thresholds/ambiguity; reorder math vs hand-computed fixtures; ledger txn/undo invariants (balance always = Σ credits − Σ payments).
- **E2E scripted:** transcript fixture → `parse→resolve→propose→confirm` → assert exact DB state. ~15 scenarios covering all intents + undo + deny.
- **Failure injection:** STT garbles a number ("paanch sau"→"paanch so") → expect graceful unresolved, not wrong write; unknown name; API 500 → UI error card, no partial write.
- **One command:** `env -u PYTHONPATH PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 .venv/bin/python -m pytest tests/ -q` (ROS `PYTHONPATH` workaround stays — AGENTS.md).

---

## 10. Schedule (4–5 h/day you + me in parallel)

| Date | Me (parallel, no API needed) | You |
|---|---|---|
| Oct 19–20 | `bolta/` scaffold: ledger+seed+parse v0+say.py, tests | — |
| Oct 21 | `commands.json` (~80) + resolve/actions | skim commands for realism |
| Oct 22 | respond/say + confirm flow + pipeline | — |
| Oct 23 | `bolta_app.py` v1 live path | try it, report clunky bits |
| Oct 24 | eval runner + dry-run | **approve 420-call run** |
| Oct 25 | fire command-eval, first numbers | — |
| **Oct 26** | **FEATURE FREEZE** — real-clip eval, bugfix only | record remaining clips (te, teleng, phone-call, fan) |
| Oct 27–28 | replay assets, README, honest results write-up | demo takes ×2, listen-check transcripts |
| Oct 29 | packaging: README diagram, MODELS_USED.md, freeze | dashboard credit count, final check |
| **Oct 30** | — | **public post live** (LinkedIn+X, hashtags+tag) |
| Nov 1–8 | bugfix only | reply to comments (engagement!), submit ≤ Nov 8 |

**Scope-cut order** (drop first if slipping): teleng command split → reorder-suggestion tuning → te commands → eval matrix breadth → stock-page visuals. Never cut: parse core, confirm/undo, replay mode, measured results.

---

## 11. Demo & submission package

**60-s script:** 0–5 hook line · 5–15 noisy-shop toggle ON, speak "Rahul ka paanch sau udhaar likho" over phone-sim → garbled raw transcript · 15–30 enhance ON → clean parse → confirm card → Timbre read-back 🔊 · 30–40 stock check + reorder answer spoken · 40–50 the heatmap: action-success vs noise, before/after bars · 50–60 "measured, not claimed — Gnani Prisma v2.5 + Timbre v2.5, repo in post."
**Headline chart:** grouped bars — action-success % per condition, raw vs enhanced.
**Written explanation:** MODELS_USED.md gains a Bolta section (Prisma verbatim→canonical→rules-parser; Timbre read-back + command synthesis).
**Post outline:** hook GIF/video → "works in a noisy shop — measured" → 3 bullet results → repo link → hashtags + @Gnani.
**Award fit:** Noise Canceller ★★★, Mixed Vibes ★★, Real Deal ★★, Solo Ninja, Demo Day Drop, Main Character (Telugu).

---

## 12. Top 8 risks → fallbacks

1. **API down on demo day** (it was, Oct 14–16) → replay mode + cached calls + pre-rendered video; never live-dependent.
2. **Parser misses real phrasing** → catalog-bounded slots, honest "samajh nahi aaya," confirm card, grammar grown from YOUR real transcripts.
3. **Prisma mangles numbers in noise** → read-back confirmation means a bad parse is *caught*, never written; entity-accuracy reported separately.
4. **Timbre 5xx on read-back** → text confirm card alone still completes flow; pre-baked phrase cache.
5. **Credit burn** → dry-run counter + your approval >10% + disk cache. Budget ≈ 620 calls total.
6. **en-IN/hi-IN script mismatch on Hinglish** → parser consumes both canonical forms; fallback hi-IN retry when parse is empty.
7. **Duplicate/ambiguous names** → disambiguation options, never silent-pick; `unresolved` → "naya customer?"
8. **Scope creep / schedule slip** → hard freeze Oct 26 + cut list above; replay-able demo always works even half-finished.

---

## 13. Definition of done

| Milestone | Done = |
|---|---|
| Ledger core | `pytest test_ledger` green; seeded DB has ≥20 products, ≥10 customers, 90-day history; undo restores exact balance |
| Parser | all intents × 3 scripts unit-tested; e2e fixtures reach correct DB state; unknown input → `unknown`, never a guess |
| Voice loop | speak→confirm→write→read-back works live; ≥15 pre-baked TTS replies cached; replay mode needs zero calls |
| Command eval | `command_eval.json` has intent/slot/action-success per condition; heatmap rendered; dry-run count verified ≤ budget |
| Real-world | ≥10 clips in data/real scored through the command pipeline |
| Demo-ready | 60-s video recorded; post live; README + MODELS_USED updated; `pytest` one-command green |

## What I need from you

1. Dashboard credit balance (app.gnani.ai/voice) — one number.
2. Record ~10 more clips: Telugu, Telenglish, phone-call, fan — real commands this time ("Rahul ka udhaar kitna hai").
3. Verify parse output on your own transcripts as I land it.
4. Approve the ~420-call eval run when it shows the dry-run count.
5. Your LinkedIn/X handle for the post plan.
