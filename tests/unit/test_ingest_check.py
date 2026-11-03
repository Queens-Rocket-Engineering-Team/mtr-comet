import numpy as np

from comet.core.types import Channel
from comet.ingest.checks import railed


def test_railed_flags_samples_beyond_range():
    ch = Channel("x", np.arange(5.0), np.array([1.0, 2.0, 99.0, 2.0, 1.0]), "psi")
    faults = railed(ch, 0.0, 50.0)
    assert [f.kind for f in faults] == ["railed"]
    assert (faults[0].region.start, faults[0].region.end) == (2.0, 2.0)
    assert railed(ch, 0.0, 100.0) == []
