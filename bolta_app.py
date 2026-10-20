"""Bolta Khata — voice ledger for kirana shops.

Run:   .venv/bin/python -m streamlit run bolta_app.py
Open:  http://localhost:8501

Pages: Counter (speak -> confirm -> written), Khata (ledger + undo),
Stock (levels + reorder), Replay (cached audio, zero API calls).
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
import time
from pathlib import Path

import soundfile as sf
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent))

from noiselab import api
from noiselab.degrade import degrade

from bolta.actions import apply, propose
from bolta.eval_commands import AUDIO_DIR
from bolta.ledger import Ledger
from bolta.parse import parse
from bolta.pipeline import listen
from bolta.reorder import suggestions
from bolta.respond import voice_for
from bolta.seed import seed

load_dotenv()

st.set_page_config(page_title="Bolta Khata", page_icon="🧾", layout="wide")

DB_PATH = Path("data/ledger.db")
STT_LANGS = {"Hinglish / Roman": "en-IN", "Hindi / Devanagari": "hi-IN",
             "Telugu": "te-IN"}

CANNED = [
    "Rahul ne paanch sau rupaye diye.",
    "Do kilo chini bik gayi.",
    "Mohan ne do kilo chini liya udhaar par.",
    "Sunita ka udhaar kitna hai.",
    "Maggi kitni bachi hai.",
    "Pachaas packet Parle-G aaye hain.",
    "Kal kya order karna chahiye.",
    "Undo karo last entry.",
]

st.session_state.setdefault("api_stt", 0)
st.session_state.setdefault("api_tts", 0)
st.session_state.setdefault("test_mode", False)


# ------------------------------------------------------- API call counting
# Wrapping the two real network entry points; cache hits never reach them.
if not getattr(api, "_calls_counted", False):
    _orig_transcribe = api.transcribe
    _orig_synth = api.synth

    def _counted_transcribe(*a, **k):
        st.session_state["api_stt"] += 1
        return _orig_transcribe(*a, **k)

    def _counted_synth(text, voice, language, out_path, **k):
        if not api.synth_is_cached(
                text, voice, language,
                model=k.get("model", "timbre-v2.5"),
                sample_rate=k.get("sample_rate", 16000)):
            st.session_state["api_tts"] += 1
        return _orig_synth(text, voice, language, out_path, **k)

    api.transcribe = _counted_transcribe
    api.synth = _counted_synth
    api._calls_counted = True


# --------------------------------------------------------------- database
@st.cache_resource
def get_db() -> Ledger:
    db = Ledger(DB_PATH)
    seed(db)          # idempotent — seeds only when products table is empty
    return db


db = get_db()


def _tmp_wav(x, sr) -> str:
    p = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    sf.write(p, x, sr, subtype="PCM_16")
    return p


def _speak(text: str, lang_key: str):
    """Timbre read-back. Test mode only plays pre-cached phrases."""
    voice, tts_lang = voice_for(lang_key)
    if st.session_state.test_mode and not api.synth_is_cached(
            text, voice, tts_lang):
        st.caption("🔇 voice reply skipped (test mode — not pre-baked)")
        return
    try:
        p = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
        api.synth(text, voice, tts_lang, p)
        st.audio(p, autoplay=True)
    except Exception:  # noqa: BLE001
        st.caption("🔇 Voice reply failed — API unreachable or credits over.")


def _confirmed_speech(prop, lang_key: str) -> str:
    t = prop.speak(lang_key)
    for q in ("Sahi hai?", "सही है?"):
        t = t.replace(q, "")
    tail = " लिख दिया।" if lang_key == "hi" else " Likh diya."
    return t.strip() + tail


def _post_write_metric(prop) -> str:
    """Plain-English updated balance/stock after a write."""
    op = prop.ops[0] if prop.ops else {}
    parts = []
    if op.get("customer_id"):
        cid = op["customer_id"]
        name = next((c["name"] for c in db.customers() if c["id"] == cid),
                    "customer")
        parts.append(f"**{name} ka udhaar ab: "
                     f"₹{db.balance_paise(cid) // 100}**")
    if op.get("product_id"):
        pid = op["product_id"]
        name = next((p["name_en"] for p in db.products() if p["id"] == pid),
                    "item")
        parts.append(f"**{name} stock ab: {db.stock(pid):g}**")
    return " · ".join(parts)


def _results(prop, transcript: str, lang_key: str):
    st.divider()
    st.markdown(f"**Heard:** {transcript}")
    st.markdown(f"**Intent:** `{prop.intent}` "
                f"(confidence {prop.confidence:.2f})")

    if prop.error or prop.intent == "unknown":
        st.error("Samajh nahi aaya — " + prop.description)
        _speak(prop.speak(lang_key), lang_key)
        return

    needs_yes = prop.needs_confirm or prop.intent == "undo"
    if not needs_yes:
        st.success(prop.description)
        _speak(prop.speak(lang_key), lang_key)
        st.session_state.pop("prop", None)
        return

    st.warning(f"**Confirm karo:** {prop.description}")
    c1, c2 = st.columns(2)
    if c1.button("✅ Haan, likh do", type="primary",
                 use_container_width=True):
        aid = db.propose({"transcript": transcript, "intent": prop.intent})
        try:
            tid = apply(prop, db, transcript=transcript, audit_id=aid)
        except Exception:  # noqa: BLE001
            st.error("Likhne mein problem aayi — database check karo. "
                     "Kuch save nahi hua.")
            return
        st.success("Likha gaya ✅ " + prop.description)
        metric = _post_write_metric(prop)
        if metric:
            st.markdown(metric)
        _speak(_confirmed_speech(prop, lang_key), lang_key)
        st.session_state.pop("prop", None)
    if c2.button("❌ Nahi, cancel", use_container_width=True):
        st.info("Theek hai — kuch nahi likha.")
        st.session_state.pop("prop", None)


# ------------------------------------------------------------------ pages
def page_counter():
    st.header("🎙️ Counter — bol ke likho")

    st.markdown("#### 1️⃣ Audio")
    audio_bytes = None
    canned = None
    if st.session_state.test_mode:
        canned = st.selectbox("Canned command (no API used)", CANNED)
    else:
        tab_mic, tab_up = st.tabs(["🎤 Record", "📁 Upload"])
        with tab_mic:
            rec = st.audio_input("bolo")
            if rec:
                audio_bytes = rec.read()
        with tab_up:
            up = st.file_uploader("wav / flac / mp3 / ogg",
                                  type=["wav", "flac", "mp3", "ogg"])
            if up:
                audio_bytes = up.read()

    st.markdown("#### 2️⃣ Language")
    lang = STT_LANGS[st.selectbox("speech language", list(STT_LANGS),
                                  index=0, label_visibility="collapsed")]
    lang_key = "hi" if lang == "hi-IN" else "hinglish"

    st.markdown("#### 3️⃣ Noisy shop?")
    noisy = st.checkbox("simulate a loud shop on this audio",
                        disabled=st.session_state.test_mode)
    noise_kind = st.selectbox("noise type",
                              ["fan", "traffic", "babble", "phone"],
                              label_visibility="collapsed",
                              disabled=not noisy)

    st.markdown("#### 4️⃣ Process")
    if not st.button("▶️  Suno + samjho", type="primary",
                     use_container_width=True):
        if st.session_state.get("prop"):
            _results(st.session_state.prop,
                     st.session_state.last_transcript,
                     st.session_state.last_langkey)
        return

    if st.session_state.test_mode:
        transcript = canned
    else:
        if not audio_bytes:
            st.warning("Pehle audio record ya upload karo.")
            return
        try:
            x, sr = sf.read(io.BytesIO(audio_bytes), dtype="float32",
                            always_2d=True)
            x = x[:, 0]
        except Exception:  # noqa: BLE001
            st.error("Ye audio file nahi chal saki — wav ya mp3 try karo.")
            return
        if noisy:
            if noise_kind == "phone":
                x, sr = degrade(x, sr, phone=True, seed=0)
            else:
                x, sr = degrade(x, sr, noise=noise_kind, snr_db=10, seed=0)
            st.caption("🔊 dukaan wali awaaz:")
            st.audio(_tmp_wav(x, sr))
        with st.spinner("Prisma sun raha hai…"):
            try:
                transcript = listen(_tmp_wav(x, sr), lang).get(
                    "transcript", "")
            except Exception:  # noqa: BLE001
                st.error("Prisma ne suna nahi — internet ya API credits "
                         "check karo, phir dobara try karo.")
                return

    st.session_state.last_transcript = transcript
    st.session_state.last_langkey = lang_key
    try:
        st.session_state.prop = propose(parse(transcript, lang), db)
    except Exception:  # noqa: BLE001
        st.error("Command samajhne mein error aaya — dobara bolo.")
        return
    _results(st.session_state.prop, transcript, lang_key)


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
            "time": time.strftime("%d %b %H:%M", time.localtime(r["ts"])),
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
    st.dataframe([{"product": p["name_en"], "stock": p["stock"],
                   "unit": p["unit"], "pack": p["pack_size"]}
                  for p in db.products()], use_container_width=True)

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
    e = by_id[st.selectbox("command", list(by_id))]
    d = AUDIO_DIR / e["id"]
    wavs = sorted(d.glob("*.wav")) if d.exists() else []
    if not wavs:
        st.info("Abhi koi replay audio nahi — "
                "pehle scripts/run_command_eval.py chalao.")
        return
    wav = st.selectbox("condition", wavs, format_func=lambda p: p.stem)
    st.audio(str(wav))
    cached = api.cache_lookup(wav, e["stt_lang"])
    if not cached:
        st.info("Is clip ka transcript cached nahi hai.")
        return
    st.write("**transcript:**", cached.get("transcript", ""))
    st.write("**expected:**", e["expected"])
    try:
        prop = propose(parse(cached.get("transcript", ""), e["stt_lang"]),
                       db)
        st.write(f"**parsed:** `{prop.intent}` — {prop.description}")
    except Exception:  # noqa: BLE001
        st.error("Is command ko parse nahi kar saka.")


# ---------------------------------------------------------------- sidebar
st.sidebar.title("🧾 Bolta Khata")
page = st.sidebar.radio("page", ["Counter", "Khata", "Stock", "Replay"])

st.sidebar.divider()
st.sidebar.markdown(
    f"**API calls this session**\n\n"
    f"STT `{st.session_state.api_stt}` · TTS `{st.session_state.api_tts}`")
st.sidebar.caption("only real (uncached) calls counted; retries may add a "
                   "few extra")

st.sidebar.toggle("🧪 Test without API (canned commands)",
                  key="test_mode")

if st.sidebar.button("🔄 Reset demo data"):
    db.close()
    DB_PATH.unlink(missing_ok=True)
    st.cache_resource.clear()
    for k in ("prop", "last_transcript", "last_langkey"):
        st.session_state.pop(k, None)
    st.rerun()

try:
    {"Counter": page_counter, "Khata": page_khata,
     "Stock": page_stock, "Replay": page_replay}[page]()
except Exception:  # noqa: BLE001
    st.error("Page load nahi hua — refresh karke dobara try karo.")
