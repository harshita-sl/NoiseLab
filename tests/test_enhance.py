"""Tests for noiselab.enhance."""

import numpy as np
import pytest

from noiselab.enhance import (CANDIDATE_CHAINS, enhance, highpass, loudnorm,
                              specgate, vad_trim)
from noiselab.degrade import make_noise, mix_at_snr, rms

SR = 16000


def _speech_with_tails():
    t = np.arange(SR) / SR
    core = 0.3 * np.sin(2 * np.pi * 300 * t)
    pad = np.zeros(int(0.5 * SR))
    return np.concatenate([pad, core, pad]).astype(np.float32)


class TestPrimitives:
    def test_highpass_kills_rumble(self):
        t = np.arange(SR) / SR
        x = (0.4 * np.sin(2 * np.pi * 40 * t)   # deep rumble
             + 0.1 * np.sin(2 * np.pi * 1000 * t)).astype(np.float32)
        y = highpass(x, SR, cutoff=100)
        spec = np.abs(np.fft.rfft(y))
        e40 = spec[int(40 * len(y) / SR)]
        e1000 = spec[int(1000 * len(y) / SR)]
        assert e1000 > 5 * e40  # input ratio was 0.25 -> ~40x attenuation

    def test_loudnorm_hits_target(self):
        x = _speech_with_tails() * 0.01
        y = loudnorm(x, SR, target_rms=0.1)
        assert abs(rms(y) - 0.1) < 0.02

    def test_vad_trims_silence(self):
        x = _speech_with_tails()
        y = vad_trim(x, SR)
        assert len(y) < len(x) - 0.5 * SR  # most padding gone
        assert len(y) > 0.8 * SR           # speech kept

    def test_specgate_denoises(self):
        clean = _speech_with_tails()
        noisy = mix_at_snr(clean, make_noise("fan", len(clean), SR, seed=0), 5)
        den = specgate(noisy, SR)
        assert len(den) == len(noisy)
        # residual noise energy in the (previously silent) tail should drop
        tail = slice(-int(0.4 * SR), None)
        assert rms(den[tail]) < rms(noisy[tail])


class TestChain:
    def test_none_passthrough(self):
        x = _speech_with_tails()
        np.testing.assert_array_equal(enhance(x, SR, "none"), x)

    def test_chains_run(self):
        x = _speech_with_tails()
        for chain in CANDIDATE_CHAINS:
            y = enhance(x, SR, chain)
            assert len(y) > 0 and np.isfinite(y).all()

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            enhance(_speech_with_tails(), SR, "bogus")
