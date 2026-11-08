import numpy as np
import pytest

from comet.models.injector import spi_mass_flow


def test_spi_mass_flow_by_hand():
    """1 cm^2 at 800 kg/m^3 and 10 bar: 1e-4 * sqrt(2 * 800 * 1e6) = 4 kg/s."""
    assert spi_mass_flow(1e-4, 800.0, 1e6) == pytest.approx(4.0)
    assert spi_mass_flow(1e-4, 800.0, 1e6, cd=0.5) == pytest.approx(2.0)


def test_spi_mass_flow_clips_negative_drop_and_takes_arrays():
    flow = spi_mass_flow(1e-4, 800.0, np.array([1e6, 0.0, -1e5]))
    assert flow.tolist() == pytest.approx([4.0, 0.0, 0.0])
