"""Corpus sanity checks: schema, entity coverage, canonical self-consistency."""

import json
from pathlib import Path

import pytest

from noiselab.normalize import canonical, normalize_text

CORPUS = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "corpus.json")
    .read_text(encoding="utf-8")
)
ENTRIES = CORPUS["entries"]

VALID_STT = {"bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
             "mr-IN", "pa-IN", "ta-IN", "te-IN"}
VALID_TTS = {"auto", "hi-IN", "en-IN", "ta-IN", "te-IN", "kn-IN", "ml-IN",
             "mr-IN", "pa-IN", "bn-IN", "gu-IN", "hi-en"}
ENT_TYPES = {"amount", "quantity", "name", "date", "time", "product"}


def test_size_and_ids_unique():
    assert 40 <= len(ENTRIES) <= 80
    ids = [e["id"] for e in ENTRIES]
    assert len(ids) == len(set(ids))


def test_required_fields_and_langs():
    for e in ENTRIES:
        for field in ("id", "split", "tts_text", "ref", "voice",
                      "tts_lang", "stt_lang", "entities"):
            assert field in e, f"{e.get('id')} missing {field}"
        assert e["stt_lang"] in VALID_STT
        assert e["tts_lang"] in VALID_TTS
        assert isinstance(e["entities"], list) and e["entities"]
        for ent in e["entities"]:
            assert ent["type"] in ENT_TYPES


def test_entity_values_present_in_canonical_ref():
    """Every marked entity value must appear in the canonicalized reference."""
    for e in ENTRIES:
        cref = canonical(e["ref"])
        for ent in e["entities"]:
            assert normalize_text(ent["value"]) in cref or \
                ent["value"] in cref, \
                f"{e['id']}: entity {ent} not found in canonical ref '{cref}'"


def test_split_counts():
    splits = {}
    for e in ENTRIES:
        splits[e["split"]] = splits.get(e["split"], 0) + 1
    assert set(splits) == {"hi", "hinglish", "mr", "te", "teleng"}
    for s in ("hi", "hinglish", "mr"):
        assert splits[s] >= 12
    for s in ("te", "teleng"):
        assert splits[s] >= 5
