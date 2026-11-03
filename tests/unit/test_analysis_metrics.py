import numpy as np
import pytest

from comet.analysis.metrics import oxidizer_mass_flow, oxidizer_mass_used
from comet.core.types import Channel, Region

RAMP = Channel(
    "mass",
    times=np.linspace(0.0, 10.0, 11),
    values=np.linspace(10.0, 0.0, 11),
    unit="kg",
)


def test_oxidizer_mass_flow_linear_ramp():
    """A tank draining 10 kg in 10 s flows at exactly 1 kg/s, positive."""
    flow = oxidizer_mass_flow(RAMP, Region("cold_flow", 2.0, 8.0))

    assert flow.unit == "kg/s"
    assert flow.times[0] == 2.0 and flow.times[-1] == 8.0
    assert np.allclose(flow.values, 1.0)


def test_oxidizer_mass_used_linear_ramp():
    """Steady 1 kg/s drain: mean over the 2s before t=2 is 9 kg, mass at t=8 is 2 kg."""
    assert oxidizer_mass_used(RAMP, Region("burn", 2.0, 8.0)) == pytest.approx(7.0)
