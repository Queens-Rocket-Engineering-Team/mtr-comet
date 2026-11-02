import numpy as np
import pytest

from comet.analysis.detectors import tank_pressure_drop
from comet.core.types import Channel, Region


def test_detector_tank_pressure_drop():
    d = np.genfromtxt(
        "tests/data/cold-flow-2026-03-06-slice.csv", delimiter=",", names=True
    )
    pressure = Channel("PTRun", d["device_timestamp_s"], d["PTRun_psi"], unit="psi")

    flow_region = tank_pressure_drop(pressure)

    assert flow_region == Region(
        "cold_flow",
        pytest.approx(89186.5, abs=0.5),  # type: ignore[ty:invalid-argument-type]
        pytest.approx(89195.3, abs=0.5),  # type: ignore[ty:invalid-argument-type]
    )
