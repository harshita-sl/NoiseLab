"""Spoken + text reply templates.

Two voices by language: hi-IN -> Devanagari via Nalini;
hinglish/en -> Latin via Poorvi (hi-en). All TTS text goes through
bolta.say for numbers (spoken words, not digits).
"""

from __future__ import annotations

VOICE_HI = ("Nalini", "hi-IN")
VOICE_HINGLISH = ("Poorvi", "hi-en")
VOICE_TE = ("Suhana", "te-IN")

ACK_HI = "ठीक है, लिख दिया।"
ACK_ROM = "Theek hai, likh diya."
ASK_HI = "सही है?"
ASK_ROM = "Sahi hai?"
DENY_HI = "ठीक है, नहीं लिखा।"
DENY_ROM = "Theek hai, nahi likha."
UNDONE_HI = "आखिरी एंट्री हटा दी।"
UNDONE_ROM = "Aakhiri entry hata di."
REASK_HI = "दोबारा बोलो।"
REASK_ROM = "Dobara bolo."


def voice_for(lang: str) -> tuple[str, str]:
    """(voice, tts_lang) for reply synthesis."""
    if lang in ("hi", "hi-IN", "mr-IN"):
        return VOICE_HI
    if lang in ("te", "te-IN"):
        return VOICE_HI  # replies stay Hindi; te spoken responses out of scope
    return VOICE_HINGLISH
