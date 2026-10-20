"""say.py round-trip: spoken words must parse back to the same digits."""

import pytest

from bolta.say import say_amount, say_hi, say_hinglish
from noiselab.normalize import numbers_to_digits


@pytest.mark.parametrize("n", [0, 1, 7, 10, 17, 21, 40, 50, 55, 90, 99,
                               100, 101, 240, 500, 750, 999, 1000, 1500,
                               2100, 5200, 25000, 100000, 250000, 987654])
def test_hi_roundtrip(n):
    assert numbers_to_digits(say_hi(n)) == str(n)


@pytest.mark.parametrize("n", [1, 20, 100, 500, 750, 1000, 2500, 15000])
def test_hinglish_roundtrip(n):
    assert numbers_to_digits(say_hinglish(n)) == str(n)


def test_amount_phrasing():
    assert say_amount(50000, "hinglish") == "paanch sau rupaye"
    assert say_amount(50000, "hi") == "पाँच सौ रुपये"
    assert say_amount(0) == "zero rupaye"
