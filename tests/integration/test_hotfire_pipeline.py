from pathlib import Path

import pytest

import comet.api
from comet.analysis.detectors import liquid_phase, thrust_above
from comet.analysis.metrics import (
    burn_time,
    injector_pressure_drop,
    oxidizer_mass_used,
    total_impulse,
)
from comet.core.regions import mean
from comet.ingest import ingest


def test_hotfire_mass_used_from_csv():
    run = ingest(Path("tests/data/hot-fire-2026-07-11.yaml"))

    thrust = run.channel("thrust")

    burn = thrust_above(thrust)

    assert burn.kind == "burn"
    assert oxidizer_mass_used(run.channel("tank_mass"), burn) == pytest.approx(
        7.5, abs=0.2
    )
    assert total_impulse(run.channel("thrust"), burn) == pytest.approx(15160, rel=0.01)
    assert burn_time(burn) == pytest.approx(7.2, abs=0.1)
    assert mean(
        injector_pressure_drop(
            run.channel("preinjector_pressure"), run.channel("chamber_pressure"), burn
        ),
        burn,
    ) == pytest.approx(184, abs=2)


def test_hotfire_discharge_coefficient_through_api():
    run = ingest(Path("tests/data/hot-fire-2026-07-11.yaml"))
    burn = thrust_above(run.channel("thrust"))
    liquid = liquid_phase(run.channel("chamber_pressure"))

    regions = {"liquid_phase": liquid}
    cd = comet.api.compute(run, "discharge_coefficient", burn, regions)

    assert cd == pytest.approx(0.353, abs=0.01)
