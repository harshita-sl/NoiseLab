"""Unit tests for noiselab.normalize — the scoring foundation."""

import pytest

from noiselab.normalize import canonical, normalize_text, numbers_to_digits


class TestNormalizeText:
    def test_empty_and_none(self):
        assert normalize_text(None) == ""
        assert normalize_text("") == ""
        assert normalize_text("   ") == ""

    def test_latin_lowercase_punct_stripped(self):
        assert normalize_text("Rahul ne 500 rupaye diye.") == \
            "rahul ne 500 rupaye diye"

    def test_devanagari_punct_and_danda(self):
        # candrabindu folds to anusvara: पाँच -> पांच
        assert normalize_text("राहुल ने आज पाँच सौ रुपये दिए।") == \
            "राहुल ने आज पांच सौ रुपये दिए"

    def test_candrabindu_folds_to_anusvara(self):
        # पाँच (candrabindu) == पांच (anusvara) — observed API variant
        assert normalize_text("पाँच") == normalize_text("पांच")

    def test_rupaye_variants_fold(self):
        # रुपए is what Prisma actually emitted for रुपये
        assert normalize_text("पांच सौ रुपए") == normalize_text("पाँच सौ रुपये")

    def test_devanagari_digits_to_ascii(self):
        assert normalize_text("५००") == "500"
        assert normalize_text("₹५,०००") == "5000"

    def test_currency_symbol_and_grouping(self):
        assert normalize_text("₹5,000") == "5000"
        assert normalize_text("₹2,50,000") == "250000"

    def test_rs_token_dropped(self):
        assert normalize_text("Rs 500") == "500"
        assert normalize_text("rs. 500") == "500"


class TestNumbersToDigits:
    @pytest.mark.parametrize("words,digits", [
        ("पाँच", "5"),
        ("पाँच सौ", "500"),
        ("सात सौ पचास", "750"),
        ("बीस", "20"),
        ("दो हज़ार", "2000"),
        ("दो लाख चालीस हज़ार", "240000"),
        ("पाँच लाख बीस हज़ार", "520000"),
        ("नौ आठ सात", "987"),  # digit-by-digit reads collapse
    ])
    def test_hindi(self, words, digits):
        assert numbers_to_digits(words) == digits

    @pytest.mark.parametrize("words,digits", [
        ("five hundred", "500"),
        ("seven hundred fifty", "750"),
        ("five thousand", "5000"),
        ("two lakh forty thousand", "240000"),
        ("twenty one", "21"),
    ])
    def test_english(self, words, digits):
        assert numbers_to_digits(words) == digits

    def test_mixed_sentence(self):
        assert numbers_to_digits("आज मैगी के बीस पैकेट बिक गए") == \
            "आज मैगी के 20 पैकेट बिक गए"

    def test_non_number_tokens_untouched(self):
        assert numbers_to_digits("राहुल ने दिए") == "राहुल ने दिए"

    def test_hinglish_span(self):
        # en-IN output on Hinglish audio: Latin + number words
        assert numbers_to_digits(
            "rahul ne five hundred rupay die aur maggie k twenty packet bick gaye"
        ) == "rahul ne 500 rupay die aur maggie k 20 packet bick gaye"


class TestCanonical:
    def test_verbatim_vs_itn_values(self):
        # Numeric value matches across verbatim and ITN forms; the currency
        # word is kept (an ITN output genuinely drops it -> fair WER deletion).
        assert canonical("पाँच सौ रुपये") == "500 रुपये"
        assert canonical("₹500") == "500"
        assert canonical("five hundred rupees") == "500 rupees"

    def test_itn_native_numerals(self):
        assert canonical("₹५,०००") == "5000"

    def test_full_sentences(self):
        assert canonical("राहुल ने आज पाँच सौ रुपये दिए।") == \
            "राहुल ने आज 500 रुपये दिए"
        assert canonical("राहुल ने आज ₹500 दिए") == \
            "राहुल ने आज 500 दिए"
