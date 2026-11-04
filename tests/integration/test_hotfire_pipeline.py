from pathlib import Path

import numpy as np
import pytest

import comet.api
from comet.analysis.detectors import liquid_phase, run_valve_open, thrust_above
from comet.analysis.metrics import (
    burn_time,
    injector_pressure_drop,
    oxidizer_mass_used,
    total_impulse,
)
from comet.core.regions import crop, mean
from comet.core.types import Channel, Region, Run
from comet.ingest import ingest


@pytest.fixture(scope="module")
def hotfire_run() -> Run:
    return ingest(Path("tests/data/hot-fire-2026-07-11.yaml"))


def test_hotfire_mass_used_from_csv(hotfire_run: Run):
    thrust = hotfire_run.channel("thrust")

    burn = thrust_above(thrust)

    assert burn.kind == "burn"
    assert oxidizer_mass_used(hotfire_run.channel("tank_mass"), burn) == pytest.approx(
        7.5, abs=0.2
    )
    assert total_impulse(hotfire_run.channel("thrust"), burn) == pytest.approx(
        15160, rel=0.01
    )
    assert burn_time(burn) == pytest.approx(7.2, abs=0.1)
    assert mean(
        injector_pressure_drop(
            hotfire_run.channel("preinjector_pressure"),
            hotfire_run.channel("chamber_pressure"),
            burn,
        ),
        burn,
    ) == pytest.approx(184, abs=2)


def test_hotfire_discharge_coefficient_through_api(hotfire_run: Run):
    burn = thrust_above(hotfire_run.channel("thrust"))
    liquid = liquid_phase(hotfire_run.channel("chamber_pressure"))

    regions = {"burn": burn, "liquid_phase": liquid}
    cd = comet.api.compute(hotfire_run, "discharge_coefficient", regions)

    assert cd == pytest.approx(0.353, abs=0.01)


def test_hotfire_thrust_coefficient(hotfire_run: Run):

    thrust = hotfire_run.channel("thrust")
    burn = thrust_above(thrust)

    valve_open = run_valve_open(hotfire_run.channel("run_valve")).start

    cf = comet.api.compute(hotfire_run, "thrust_coefficient", {"burn": burn})
    assert isinstance(cf, Channel)
    window = Region("window", valve_open + 2.25, valve_open + 3.25)

    assert np.median(crop(cf, window).values) == pytest.approx(0.938, abs=0.01)


def test_hotfire_relay_bounce_is_flagged_not_the_valve(hotfire_run: Run):
    """Igniter relays bounce for 15-20 ms; the main valve's 0.27 s states are real."""
    glitched = {f.channel for f in hotfire_run.faults if f.kind == "glitch"}
    assert glitched == {"relay_IgnPrime", "relay_IgnRun"}
