"""NoiseLab demo app — Streamlit.

    .venv/bin/python -m streamlit run app.py

Modes:
- Live: upload/record -> degrade (optional) -> enhance -> transcribe both.
  Uses the API (cached, so replays are free).
- Replay: pick a benchmark audio file + its cached transcript — zero calls.
"""

from __future__ import annotations

import difflib
import json
import sys
import tempfile
from pathlib import Path

import soundfile as sf
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dotenv import load_dotenv

from noiselab import api
from noiselab.degrade import SYNTH_NOISES, degrade
from noiselab.enhance import CANDIDATE_CHAINS, enhance
from noiselab.normalize import canonical, normalize_text
from noiselab.runner import AUDIO_DIR, RESULTS_DIR, load_corpus

load_dotenv()

st.set_page_config(page_title="NoiseLab", page_icon="🎙️", layout="wide")


def _load_uploaded(file_bytes: bytes) -> tuple:
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(file_bytes)
        tmp = f.name
    x, sr = sf.read(tmp, dtype="float32", always_2d=True)
    return x[:, 0], sr


def _to_wav_bytes(x, sr) -> bytes:
    import io
    buf = io.BytesIO()
    sf.write(buf, x, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()


def _highlight_diff(ref: str, hyp: str) -> str:
    """Mark hyp tokens that differ from ref (canonical space)."""
    rt = canonical(ref).split()
    ht = canonical(hyp).split()
    sm = difflib.SequenceMatcher(None, rt, ht, autojunk=False)
    parts = []
    for tag, _i1, _i2, j1, j2 in sm.get_opcodes():
        seg = " ".join(ht[j1:j2])
        if not seg:
            continue
        parts.append(seg if tag == "equal"
                     else f"**:red[{seg}]**")
    return " ".join(parts)


def page_live():
    st.header("Live pipeline")
    lang = st.selectbox("STT language", ["hi-IN", "en-IN", "mr-IN"],
                        index=0)

    tab_up, tab_mic = st.tabs(["Upload", "Record"])
    audio_bytes = None
    with tab_up:
        up = st.file_uploader("audio file", type=["wav", "flac", "mp3", "ogg"])
        if up:
            audio_bytes = up.read()
    with tab_mic:
        rec = st.audio_input("record a clip")
        if rec:
            audio_bytes = rec.read()

    c1, c2, c3 = st.columns(3)
    noise = c1.selectbox("noise", ["as is"] + list(SYNTH_NOISES) +
                         ["phone"])
    snr = c2.selectbox("SNR dB", [None, 20, 10, 5, 0],
                       format_func=lambda v: "—" if v is None else v)
    chain = c3.selectbox("enhancer", CANDIDATE_CHAINS)

    if not audio_bytes:
        st.info("upload or record a clip to begin")
        return

    x, sr = _load_uploaded(audio_bytes)
    st.audio(audio_bytes)

    if noise == "as is":
        deg, dsr = x, sr
    elif noise == "phone":
        deg, dsr = degrade(x, sr, phone=True, seed=0)
    else:
        deg, dsr = degrade(x, sr, noise=noise, snr_db=snr or 10, seed=0)
    enh = enhance(deg, dsr, chain)

    deg_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    enh_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    sf.write(deg_wav, deg, dsr, subtype="PCM_16")
    sf.write(enh_wav, enh, dsr, subtype="PCM_16")

    st.subheader("Degraded vs enhanced audio")
    st.audio(_to_wav_bytes(deg, dsr))
    st.audio(_to_wav_bytes(enh, dsr))

    ref_text = st.text_area("reference transcript (optional — enables WER + "
                            "error highlighting)")
    if st.button("Transcribe both", type="primary"):
        with st.spinner("calling Prisma…"):
            try:
                r_raw = api.transcribe_cached(deg_wav, lang)
                r_enh = api.transcribe_cached(enh_wav, lang)
            except Exception as e:  # noqa: BLE001
                st.error(f"API error: {e}")
                return
        c1, c2 = st.columns(2)
        c1.subheader("raw degraded")
        c1.write(r_raw.get("transcript", ""))
        c2.subheader(f"enhanced ({chain})")
        c2.write(r_enh.get("transcript", ""))
        if ref_text.strip():
            from noiselab.score import score
            s_raw = score(ref_text, r_raw.get("transcript", ""))
            s_enh = score(ref_text, r_enh.get("transcript", ""))
            m1, m2, m3 = st.columns(3)
            m1.metric("WER raw", f"{s_raw.wer:.2f}")
            m2.metric("WER enhanced", f"{s_enh.wer:.2f}",
                      delta=f"{s_enh.wer - s_raw.wer:+.2f}")
            m3.metric("entity acc raw→enh",
                      f"{s_raw.entity_acc} → {s_enh.entity_acc}")
            st.markdown("**enhanced, errors highlighted:** "
                        + _highlight_diff(ref_text,
                                          r_enh.get("transcript", "")))


def page_replay():
    st.header("Replay mode (no API calls)")
    entries = {e["id"]: e for e in load_corpus("data/corpus.json")}
    entry_id = st.selectbox("corpus entry", list(entries))
    e = entries[entry_id]
    d = AUDIO_DIR / entry_id
    conds = sorted(p.stem for p in d.glob("*.wav") if p.stem != "ref") \
        if d.exists() else []
    if not conds:
        st.warning("no audio generated yet for this entry — run "
                   "run_benchmark.py first")
        return
    cond = st.selectbox("condition", conds)
    wav = d / f"{cond}.wav"
    st.audio(str(wav))
    st.write("ref:", e["ref"])
    cached = api.cache_lookup(wav, e["stt_lang"])
    if cached:
        st.write("hyp:", cached.get("transcript", ""))
        from noiselab.score import score
        s = score(e["ref"], cached.get("transcript", ""), e["entities"])
        st.metric("WER", f"{s.wer:.2f}")
    else:
        st.info("no cached transcript for this clip")


def page_results():
    st.header("Benchmark results")
    rp = RESULTS_DIR / "results.json"
    hp = RESULTS_DIR / "heatmap.png"
    if hp.exists():
        st.image(str(hp))
    if rp.exists():
        data = json.loads(rp.read_text(encoding="utf-8"))
        agg = data.get("aggregate", {})
        if agg:
            st.dataframe(
                [{"cond": k, **v} for k, v in agg.items()],
                use_container_width=True)
        st.download_button("results.json", rp.read_bytes(),
                           file_name="results.json")
    else:
        st.info("no results yet — run run_benchmark.py")


pg = st.sidebar.radio("mode", ["Live", "Replay", "Results"], index=0)
st.sidebar.caption("NoiseLab — Gnani Prisma noise-robustness benchmark")
{"Live": page_live, "Replay": page_replay, "Results": page_results}[pg]()
