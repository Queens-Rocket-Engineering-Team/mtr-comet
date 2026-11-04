import numpy as np
import pytest

from comet.analysis.properties import n2o_saturated_density


def test_n2o_saturated_density_at_50_bar():
    """Liquid N2O at 50 bar is about 789 kg/m^3; vapour there is far lighter."""
    liquid, vapour = n2o_saturated_density(
        np.array([50e5, 50e5]), np.array([True, False])
    )
    assert liquid == pytest.approx(789, abs=5)
    assert vapour < liquid / 3
