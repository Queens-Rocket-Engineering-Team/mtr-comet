import numpy as np
import pytest

from comet.core.regions import before, integrate
from comet.core.types import Channel, Region


def test_integrate_splits_exactly():
    """Test that the integral helper of two adjacent regions is equal to the
    integral of the joint region"""
    ch = Channel(
        "force",
        times=np.array([0.0, 1.0, 2.0, 3.0]),
        values=np.array([0.0, 2.0, 2.0, 0.0]),
        unit="N",
    )

    # Integrate along [0.5, 2.5]
    whole = integrate(ch, Region("burn", 0.5, 2.5))

    # Integrate along [0.5, 1.7] + [1.7, 2.5]
    parts = integrate(ch, Region("burn", 0.5, 1.7)) + integrate(
        ch, Region("burn", 1.7, 2.5)
    )

    # Verify integrals match
    assert whole == pytest.approx(parts)
    assert whole == pytest.approx(3.5)  # trapezoids by hand


def test_integrate_open_region():
    """Test that the integrate helper works properly over an open region"""
    ch = Channel(
        "force",
        times=np.array([0.0, 1.0, 2.0, 3.0]),
        values=np.array([0.0, 2.0, 2.0, 0.0]),
        unit="N",
    )

    # Integrate along [0.5, inf)
    integral = integrate(ch, Region("burn", start=0.5, end=None))

    # Verify integral
    assert integral == pytest.approx(3.75)


def test_value_at_rejects_time_outside_data():
    """Test that value_at rejects times outside of the channel's range"""
    ch = Channel("f", times=np.array([0.0, 1.0]), values=np.array([1.0, 1.0]), unit="N")
    with pytest.raises(ValueError):
        integrate(ch, before(Region("burn", 0.2, 1.0), 0.5))  # window is [-0.3, 0.2]
