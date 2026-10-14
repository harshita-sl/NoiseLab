"""Tests for noiselab.degrade: SNR accuracy, determinism, telephony sim."""

import numpy as np
import pytest

from noiselab.degrade import (
    SYNTH_NOISES, degrade, make_noise, measured_snr, mix_at_snr, rms,
    telephony,
)

SR = 16000


def _speech(n=SR):
    t = np.arange(n) / SR
    return (0.3 * np.sin(2 * np.pi * 200 * t)
            + 0.2 * np.sin(2 * np.pi * 400 * t)).astype(np.float32)


class TestNoise:
    @pytest.mark.parametrize("kind", SYNTH_NOISES)
    def test_synthetic_shapes_and_rms(self, kind):
        n = make_noise(kind, SR, SR, seed=1)
        assert n.shape == (SR,)
        assert np.isfinite(n).all()
        assert rms(n) > 0.01

    def test_deterministic(self):
        a = make_noise("traffic", 1000, SR, seed=7)
        b = make_noise("traffic", 1000, SR, seed=7)
        np.testing.assert_array_equal(a, b)
        c = make_noise("traffic", 1000, SR, seed=8)
        assert not np.array_equal(a, c)

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            make_noise("nope", 100, SR)


class TestMixAtSnr:
    @pytest.mark.parametrize("snr", [20, 10, 5, 0, -5])
    def test_achieved_snr(self, snr):
        speech = _speech()
        noise = make_noise("white", len(speech), SR, seed=0)
        mixed = mix_at_snr(speech, noise, snr)
        assert abs(measured_snr(speech, mixed) - snr) < 0.1

    def test_short_noise_looped(self):
        speech = _speech(3 * SR)
        noise = make_noise("pink", SR // 4, SR, seed=0)
        mixed = mix_at_snr(speech, noise, 10)
        assert len(mixed) == len(speech)
        assert abs(measured_snr(speech, mixed) - 10) < 0.5


class TestTelephony:
    def test_output_rate_and_bandlimit(self):
        # Broadband input: telephony must pass 500-2000 Hz strongly and
        # attenuate <300 Hz heavily (300-3400 Hz voice band).
        g = np.random.default_rng(0)
        x = g.standard_normal(SR).astype(np.float32)
        y, sr = telephony(x, SR, seed=0)
        assert sr == 8000
        assert abs(len(y) / sr - 1.0) < 0.05
        spec = np.abs(np.fft.rfft(y)) ** 2
        freqs = np.fft.rfftfreq(len(y), 1 / sr)
        lo = spec[(freqs > 100) & (freqs < 250)].mean()
        mid = spec[(freqs > 500) & (freqs < 2000)].mean()
        assert mid > 10 * lo

    def test_packet_loss_zeroes(self):
        y, _ = telephony(_speech(), SR, packet_loss=0.5, seed=3)
        assert np.sum(y == 0.0) > 0


class TestDegrade:
    def test_clean_passthrough(self):
        x = _speech()
        y, sr = degrade(x, SR)
        np.testing.assert_array_equal(x, y)
        assert sr == SR

    def test_noise_then_phone(self):
        y, sr = degrade(_speech(), SR, noise="fan", snr_db=10, phone=True)
        assert sr == 8000
        assert np.isfinite(y).all()
        assert np.max(np.abs(y)) <= 1.0
