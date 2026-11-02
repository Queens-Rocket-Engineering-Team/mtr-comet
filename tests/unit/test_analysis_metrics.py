import numpy as np

from comet.analysis.metrics import oxidizer_mass_flow
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
