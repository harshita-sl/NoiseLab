"""Tests for noiselab.score."""

from noiselab.score import aggregate, entity_hit, score


def test_perfect_match():
    s = score("पाँच सौ रुपये", "पांच सौ रुपए")  # observed API spelling variants
    assert s.wer == 0.0
    assert s.cer == 0.0


def test_number_words_match_digits():
    s = score("पाँच सौ रुपये दिए", "₹500 दिए")
    # canonical: ref "500 रुपये दिए" vs hyp "500 दिए" -> 1 deletion
    assert 0 < s.wer <= 0.34


def test_empty_hyp(self= None):
    s = score("कुछ शब्द", "")
    assert s.wer == 1.0 and s.cer == 1.0


def test_entity_hit_boundaries():
    assert entity_hit("500", "उसने 500 दिए")
    assert not entity_hit("500", "उसने 5000 दिए")
    assert entity_hit("20 जनवरी", "कल 20 जनवरी को आएगा")
    assert not entity_hit("राम", "रामायण पढ़ी")  # no partial word match


def test_score_entities():
    ents = [{"type": "amount", "value": "500"},
            {"type": "name", "value": "राहुल"}]
    s = score("राहुल ने पाँच सौ रुपये दिए", "राहुल ने ₹500 दिए", ents)
    assert s.entity_hits == 2 and s.entity_acc == 1.0
    s2 = score("राहुल ने पाँच सौ रुपये दिए", "राहुल ने ₹50 दिए", ents)
    assert s2.entity_hits == 1  # राहुल hit, 500 missed (50 != 500)


def test_aggregate_by_key():
    rows = [
        {"cond": "clean", "score": score("a b", "a b").to_dict()},
        {"cond": "clean", "score": score("a b", "a c").to_dict()},
        {"cond": "noisy", "score": score("a b", "x y").to_dict()},
    ]
    agg = aggregate(rows, key="cond")
    assert agg["clean"]["n"] == 2 and agg["clean"]["wer"] == 0.25
    assert agg["noisy"]["wer"] == 1.0
