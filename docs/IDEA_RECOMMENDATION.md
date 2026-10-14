# App-on-top idea recommendation — for decision

*Built on verified rules in [HACKATHON_BRIEF.md](HACKATHON_BRIEF.md). Written Oct 14, 2026.*

## Frame first — what actually wins this

Two separate games:

1. **Internship shortlist = verified engagement** on the nominated LinkedIn/X
   post. The post must be live *before* submission. This is the gate that
   decides whether anyone interviews you — so the app's job is to demo
   extremely well in ≤60 s, early, and shareably.
2. **Awards** are judged per-category, independent of shortlist. One award
   max per person.

Constraints that shape the choice:

- **No Evon on the API.** Intent extraction must be rules/templates or a
  non-Gnani LLM. Rules are *fine* for a bounded domain — and arguably better
  for the demo (deterministic). Using an outside LLM is not explicitly banned
  ("must genuinely use Gnani tech" is the requirement), but a rules-based
  parser is zero-risk and zero-cost. **Recommendation: rules only.**
- **Noise-robustness is our moat.** Anyone can build a kirana voice bot on
  clean audio. Almost nobody will bring an *instrumented* before/after
  measurement harness. The app should be chosen so the NoiseLab story is the
  spine of the demo, not an appendix.
- ~2–3 h/day until Oct 29 → the app must be small: one flow, one screen,
  one gimmick that survives noise.

## Candidate evaluation

| Idea | NoiseLab fit | Finishable by 10/29 | Needs Evon? | Crowded? | Shareable demo | Award fit | Harm if wrong |
|---|---|---|---|---|---|---|---|
| **Bolta Kirana** (voice ledger) | ★★★ shops are noisy; amounts/quantities are exactly our entity metric | high — one parse flow | no (rules) | high — it's a literal Gnani example | high — "still works over a bad phone line" is a 5-second story | Noise Canceller, Mixed Vibes, Real Deal, Solo Ninja, Demo Day Drop | low — bad row in a personal ledger |
| KrishiSaarthi (farmer advisory) | ★★ | low — needs a trusted KB (schemes/weather data) or it hallucinates advice | semi — answers need generation | high — also a Gnani example | medium | Real Deal, Main Character | **high** — wrong advice to a farmer is a trust disaster |
| Panchayat grievance desk | ★★ | medium — ticket schema + dashboard doubles scope | semi — complaint→category w/o LLM is brittle | low-med | medium | Real Deal | low |
| ASHA visit register | ★★★ dictation→structured form is exactly entity extraction | high | no | low | medium | Real Deal, Main Character | low-med — structured note, no advice |
| Bol-ke-Form (voice→PDF) | ★★ | medium — PDF gen + field mapping is extra plumbing | no | low | medium | Jugaad Genius | low |
| Viva Buddy (oral exam practice) | ★ | low — needs evaluative feedback; rules give shallow feedback, demo feels thin | yes-ish | low | medium | Jugaad Genius | low |

## Ranked recommendation

### 1. **"Bolta Khata" — the voice ledger that survives noise** ✅ recommended

One flow: shopkeeper says "Rahul ka paanch sau udhaar hai" in a shop full of
fan + grinder + traffic noise (or *over a phone call*) → NoiseLab-enhanced
audio → Prisma → rules extract {party, amount, direction, item?} → **Timbre
reads the entry back for confirmation** ("Rahul, paanch sau rupaye udhaar —
theek hai?") → ledger JSON updates. If confidence is low, the app asks a
clarifying question — that read-back loop *is* the robustness story made
visible.

Why it wins despite being a "crowded" idea: crowding matters less than you
think because the submission is judged as *application + evidence*. Every
competitor ships a kirana bot; you'll ship a kirana bot **with a measured
WER/entity-accuracy heatmap showing it works at 0 dB SNR over 8 kHz
telephony**. That gap in rigor is the differentiator, and it's honest —
which the rules explicitly reward ("a demo that fakes a result will cost you
more than one that shows an honest limitation").

Award fit: Noise Canceller (the obvious one), Mixed Vibes (Hinglish ledger),
Real Deal (kirana is literally named in the criteria), Solo Ninja, Demo Day
Drop.

### 2. ASHA voice visit register — strong backup

Same mechanics (dictation → structured form), slightly less flashy demo but
less crowded and a genuinely underserved user. Keep this if the kirana space
feels too noisy or read-back confirmation doesn't land.

### 3. Panchayat grievance desk — distant third

Good mission, but complaint→category is weak without an LLM and a dashboard
doubles UI scope.

## Two-week build plan (winner: Bolta Khata)

| Days | Work |
|---|---|
| Oct 15–16 | Benchmark run on API (already built): results.json + heatmap committed. **Post #1 teaser**: "measuring how noise breaks Indic STT" w/ heatmap |
| Oct 17–19 | run_enhance_eval across chains → pick best-per-noise-profile; write honest results section |
| Oct 20–22 | Bolta Khata core: record → (degrade sim toggle) → enhance → Prisma → slot parser {party, amount, dir} → Timbre read-back confirm → ledger view. Keep it one Streamlit page on top of `noiselab/` |
| Oct 23–24 | edge cases: low-confidence ask-again path, "cancel" handling, Marathi/Hinglish entries, empty-audio guard |
| Oct 25–26 | record 20–30 real clips (own voice, real noise) → score_real.py → real-world table |
| Oct 27–28 | demo video x2 takes + written explanation + README polish |
| Oct 29 | buffer + final commit |
| **Oct 30** | **public demo post live** (LinkedIn + X, both hashtags, tag Gnani) |
| Nov 1–8 | respond to comments (counts as engagement), final submission by Nov 8 |

## 60-second demo script

- **0–5 s**: "I built a voice ledger for kirana shops — and a benchmark of how noise breaks Indian-language STT."
- **5–15 s**: speak a ledger line in Hinglish in a noisy room → show raw transcript garbled.
- **15–30 s**: toggle NoiseLab enhance → same audio → clean transcript → ledger row appears → Timbre reads it back in Hindi.
- **30–45 s**: show the heatmap: WER vs noise type × SNR, before/after bars.
- **45–60 s**: real-phone-audio clip + "all measurements, no claims — repo + data in post. Built on Gnani Prisma v2.5 + Timbre v2.5."

## Top 3 risks + fallbacks

1. **API/infra flakiness on demo day** (we already hit Cloudflare 403s and
   resets today) → the app's Replay mode plays cached audio + transcripts;
   the video can be recorded with live calls but never depends on them.
2. **Rules parser misses intent on real code-mixed speech** → constrained
   slot grammar ("<name> ka <amount> udhaar/jama"), a confirmation
   read-back, and a manual-correct tap. Parser stays honest: it *says* when
   it didn't parse instead of guessing.
3. **Real noisy audio still fails after enhancement** → report it plainly
   (the challenge rewards honest measurement), lean the demo on the
   conditions where the layer provably wins (telephony sim, fan), and keep
   clean-condition correctness as the floor.

## Blunt corrections to my assumptions, stated plainly

- **Crowding is real for kirana** — the Gnani site literally suggests it. The
  counter is differentiation-by-measurement, not a different idea.
- **Evon-free is fine.** A ledger needs ~4 slots; rules beat a 30B model you
  can't call anyway. Don't waste days fighting HF weights + GPU access.
- **"Small Town Big Build" eligibility is unverified** — it depends on your
  college/city tier; flag as a maybe, not a plan.
- **Engagement ≥ build for shortlisting** — allocate time to the post and
  replies, not just code. An average app with a great 60-s video beats a
  great app nobody sees.
- **TTS speech is cleaner than real speech** — NoiseLab's synthetic numbers
  will look better than real-world. Say so in the write-up; pretending
  otherwise is a disqualifiable "misleading demo."
