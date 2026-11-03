import numpy as np

from comet.analysis.filters import despike
from comet.core.types import Channel


def test_despike_removes_single_sample_spike():
    """Test that the despike filter correctly removes a spike sample"""
    ch = Channel("x", np.arange(5.0), np.array([1.0, 1.0, 10.0, 1.0, 1.0]), "kg")
    assert despike(ch).values.tolist() == [1.0, 1.0, 1.0, 1.0, 1.0]
