import numpy as np

from comet.core.types import Channel
from comet.ingest.checks import glitch, railed


def test_railed_flags_samples_beyond_range():
    ch = Channel("x", np.arange(5.0), np.array([1.0, 2.0, 99.0, 2.0, 1.0]), "psi")
    faults = railed(ch, 0.0, 50.0)
    assert [f.kind for f in faults] == ["railed"]
    assert (faults[0].region.start, faults[0].region.end) == (2.0, 2.0)
    assert railed(ch, 0.0, 100.0) == []


def test_glitch_flags_states_shorter_than_debounce():
    ch = Channel("v", np.arange(5) * 0.01, np.array([0, 0, 1, 0, 0]), "bool")
    faults = glitch(ch, debounce=0.05)
    assert [(f.kind, f.region.start, f.region.end) for f in faults] == [
        ("glitch", 0.02, 0.03)
    ]
    assert glitch(ch, debounce=0.005) == []
