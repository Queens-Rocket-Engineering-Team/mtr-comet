from pathlib import Path

import numpy as np
import pytest

from comet.analysis.detectors import tank_mass_drop, tank_pressure_drop, thrust_above
from comet.core.types import Channel, Region
from comet.ingest import ingest
from comet.ingest.adapter import QRETCsvAdapter


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


def test_mass_and_pressure_detectors_agree():
    run = QRETCsvAdapter().ingest(
        "tests/data/cold-flow-2026-03-06-slice.csv",
        tags={"PTRun": ["tank_pressure"], "LCFill": ["tank_mass"]},
    )
    by_pressure = tank_pressure_drop(run.channel("tank_pressure"))
    by_mass = tank_mass_drop(run.channel("tank_mass"))
    assert by_mass.start == pytest.approx(by_pressure.start, abs=1.0)
    assert by_mass.end == pytest.approx(by_pressure.end, abs=1.0)


def test_tank_detectors_agree_with_thrust_at_200hz():
    run = ingest(Path("tests/data/hot-fire-2026-07-11.yaml"))
    burn = thrust_above(run.channel("thrust"))

    assert burn.end is not None
    assert burn.end - burn.start == pytest.approx(7.2, abs=0.1)
    assert tank_pressure_drop(run.channel("tank_pressure")).start == pytest.approx(
        burn.start, abs=1.0
    )
    assert tank_mass_drop(run.channel("tank_mass")).start == pytest.approx(
        burn.start, abs=1.0
    )
