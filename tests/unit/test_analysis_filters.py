import numpy as np
import pytest

from comet.analysis.filters import despike, savitzky_golay
from comet.core.types import Channel


def test_despike_removes_single_sample_spike():
    """Test that the despike filter correctly removes a spike sample"""
    ch = Channel("x", np.arange(5.0), np.array([1.0, 1.0, 10.0, 1.0, 1.0]), "kg")
    assert despike(ch).values.tolist() == [1.0, 1.0, 1.0, 1.0, 1.0]


def test_savitzky_golay_smooths_noise_but_keeps_the_trend():
    """A quadratic fit over any window reproduces a straight line exactly."""
    t = np.arange(0.0, 10.0, 0.1)
    rng = np.random.default_rng(0)
    ch = Channel("x", t, 3.0 * t + rng.normal(0, 0.5, t.size), "N")
    smoothed = savitzky_golay(ch, window=21, polyorder=2)
    interior = slice(10, -10)  # edges are fitted with partial windows
    assert np.abs(smoothed.values[interior] - 3.0 * t[interior]).max() < 0.5
    assert np.std(smoothed.values - 3.0 * t) < np.std(ch.values - 3.0 * t)
    assert (smoothed.unit, smoothed.name) == ("N", "x")


def test_savitzky_golay_rejects_bad_window():
    ch = Channel("x", np.arange(5.0), np.ones(5), "N")
    with pytest.raises(ValueError, match="odd"):
        savitzky_golay(ch, window=4)
    with pytest.raises(ValueError, match="polyorder"):
        savitzky_golay(ch, window=5, polyorder=5)
