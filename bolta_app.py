"""Bolta Khata — voice ledger for kirana shops.

    .venv/bin/python -m streamlit run bolta_app.py

Pages:
- Counter: speak a command -> confirm card -> Timbre read-back -> write.
- Khata:   transactions + udhaar balances + undo.
- Stock:   levels + reorder suggestions.
- Replay:  canned commands + cached transcripts (zero API calls).
"""

from __future__ import annotations

import io
import sys
import tempfile
from pathlib import Path

import soundfile as sf
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

import json

from noiselab import api
from noiselab.degrade import degrade
from noiselab.enhance import CANDIDATE_CHAINS

from bolta.actions import apply, propose
from bolta.eval_commands import AUDIO_DIR
from bolta.ledger import Ledger
from bolta.parse import parse
from bolta.reorder import suggestions
from bolta.respond import voice_for
from bolta.seed import seed

load_dotenv()

st.set_page_config(page_title="Bolta Khata", page_icon="🧾", layout="wide")

DB_PATH = Path("data/ledger.db")


@st.cache_resource
def get_db() -> Ledger:
    db = Ledger(DB_PATH)
    seed(db)
    return db


db = get_db()


def _write_tmp_wav(x, sr) -> str:
    p = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    sf.write(p, x, sr, subtype="PCM_16")
    return p


def _speak(text: str, lang_key: str):
    """Timbre read-back (cached). Fails soft — text card still works."""
    voice, tts_lang = voice_for(lang_key)
    try:
        p = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        api.synth(text, voice, tts_lang, p)
        st.audio(p, autoplay=True)
    except Exception as exc:  # noqa: BLE001
        st.caption(f"(TTS unavailable: {exc})")


def _confirm_card(prop, transcript: str, lang_key: str):
    st.markdown("### Confirm karo")
    st.warning(f"**{prop.description}**")
    c1, c2 = st.columns(2)
    if c1.button("✅ Haan, likh do", type="primary", use_container_width=True):
        aid = db.propose({"transcript": transcript, "intent": prop.intent})
        tid = apply(prop, db, transcript=transcript, audit_id=aid)
        st.success("Likha gaya!" if tid else "Kuch likha nahi.")
        _speak(prop.speak(lang_key).replace("Sahi hai?", "").strip()
               + " — likh diya.", lang_key)
        st.rerun()
    if c2.button("❌ Nahi, cancel", use_container_width=True):
        st.info("Theek hai, nahi likha.")
        _speak("Theek hai, nahi likha.", lang_key)


def page_counter():
    st.header("🎙️ Counter — bol ke likho")
    lang = st.selectbox("STT language", ["en-IN", "hi-IN", "te-IN"],
                        index=0)
    lang_key = "hi" if lang == "hi-IN" else "hinglish"

    noisy = st.toggle("📢 Noisy shop mode (simulate a loud shop on your "
                      "recording)", value=False)
    col_n = st.columns(2)
    noise_kind = col_n[0].selectbox(
        "shop noise", ["fan", "traffic", "babble", "phone"],
        disabled=not noisy)
    snr = col_n[1].select_slider("SNR dB (lower = louder)",
                                 options=[20, 10, 5, 0], value=10,
                                 disabled=not noisy)
    chain = st.selectbox("enhancer chain", CANDIDATE_CHAINS, index=0)

    tab_mic, tab_up = st.tabs(["Record", "Upload"])
    audio_bytes = None
    with tab_mic:
        rec = st.audio_input("bolo")
        if rec:
            audio_bytes = rec.read()
    with tab_up:
        up = st.file_uploader("wav/flac/mp3/ogg",
                              type=["wav", "flac", "mp3", "ogg"])
        if up:
            audio_bytes = up.read()

    if not audio_bytes:
        st.info("Bolo — jaise: 'Rahul ne paanch sau diye' ya "
                "'Maggi kitni bachi hai'")
        return

    x, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32",
                    always_2d=True)
    x = x[:, 0]

    if noisy:
        if noise_kind == "phone":
            x, sr = degrade(x, sr, phone=True, seed=0)
        else:
            x, sr = degrade(x, sr, noise=noise_kind, snr_db=snr, seed=0)
        st.caption("🔊 ye sunai dega jaisa dukaan mein hai:")
        st.audio(_write_tmp_wav(x, sr))

    wav = _write_tmp_wav(x, sr)

    if st.button("Suno + samjho", type="primary"):
        with st.spinner("Prisma sun raha hai…"):
            try:
                from bolta.pipeline import listen
                res = listen(wav, lang, chain=chain)
            except Exception as exc:  # noqa: BLE001
                st.error(f"STT error: {exc}")
                return
        transcript = res.get("transcript", "")
        st.session_state["last_transcript"] = transcript
        st.session_state["last_lang"] = lang
        st.session_state["last_langkey"] = lang_key
        prop = propose(parse(transcript, lang), db)
        st.session_state["last_prop"] = prop

    prop = st.session_state.get("last_prop")
    if prop is not None:
        st.write("**Prisma ne suna:**", st.session_state["last_transcript"])
        st.write(f"**Intent:** `{prop.intent}`  "
                 f"**confidence:** {prop.confidence:.2f}")
        if prop.error or prop.intent == "unknown":
            st.error(prop.description)
            _speak(prop.speak(lang_key), lang_key)
        elif prop.needs_confirm:
            _confirm_card(prop, st.session_state["last_transcript"],
                          lang_key)
        else:
            st.success(prop.description)
            _speak(prop.speak(lang_key), lang_key)


def page_khata():
    st.header("📒 Khata")
    if st.button("↩️ Undo last entry"):
        undone = db.undo_last()
        st.warning(f"Undone: {undone['kind']} {undone['note']}"
                   if undone else "Kuch nahi tha.")
        st.rerun()

    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("Recent entries")
        rows = [{
            "time": __import__("time").strftime("%d %b %H:%M",
                                               __import__("time").localtime(r["ts"])),
            "kind": r["kind"], "who": r["customer_name"] or "—",
            "item": (f"{r['qty']:g} {r['unit']} {r['product_name']}"
                     if r["product_name"] else "—"),
            "₹": r["amount_paise"] // 100,
            "src": r["source"],
        } for r in db.recent(30)]
        st.dataframe(rows, use_container_width=True)
    with c2:
        st.subheader("Udhaar balances")
        bals = [{"customer": c["name"],
                 "udhaar ₹": db.balance_paise(c["id"]) // 100}
                for c in db.customers()]
        st.dataframe(bals, use_container_width=True)


def page_stock():
    st.header("📦 Stock")
    prods = [{"product": p["name_en"], "stock": p["stock"],
              "unit": p["unit"], "pack": p["pack_size"]}
             for p in db.products()]
    st.dataframe(prods, use_container_width=True)

    st.subheader("🔁 Kya order karna chahiye")
    sugg = suggestions(db, days=14)
    if sugg:
        st.dataframe([{"product": s["name_en"], "stock": s["stock"],
                       "sold/day": s["daily_rate"],
                       "days left": s["days_left"],
                       "order qty": s["qty"], "unit": s["unit"]}
                      for s in sugg], use_container_width=True)
    else:
        st.success("Sab stock theek hai.")


def page_replay():
    st.header("▶️ Replay (no API calls)")
    commands = json.loads(Path("data/commands.json")
                          .read_text(encoding="utf-8"))["entries"]
    by_id = {e["id"]: e for e in commands}
    entry_id = st.selectbox("command", list(by_id))
    e = by_id[entry_id]
    d = AUDIO_DIR / entry_id
    wavs = sorted(d.glob("*.wav")) if d.exists() else []
    if not wavs:
        st.warning("no audio yet — run scripts/run_command_eval.py first")
        return
    wav = st.selectbox("condition", wavs, format_func=lambda p: p.stem)
    st.audio(str(wav))
    cached = api.cache_lookup(wav, e["stt_lang"])
    if not cached:
        st.info("no cached transcript")
        return
    hyp = cached.get("transcript", "")
    st.write("**transcript:**", hyp)
    st.write("**expected:**", e["expected"])
    prop = propose(parse(hyp, e["stt_lang"]), db)
    st.write(f"**parsed:** `{prop.intent}` — {prop.description}")


pg = st.sidebar.radio("page", ["Counter", "Khata", "Stock", "Replay"],
                      index=0)
st.sidebar.caption("Bolta Khata — Gnani Prisma v2.5 + Timbre v2.5")
{"Counter": page_counter, "Khata": page_khata,
 "Stock": page_stock, "Replay": page_replay}[pg]()
