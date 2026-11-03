"""Liquid depletion time across every hotfire we have.

See tests/data/README.md for the provenance of each trace. Expected values and
tolerances are recorded per test because the ground truths differ in definition:
the hf_analysis_tools value for QRET HF4 is a 3 %-below-trend departure, McGill
marks the onset of the drop (the departure lands 0.1-0.35 s later), and Waterloo
has no published event time, so the mass-flow collapse at about 10 s is the
reference.
"""

from pathlib import Path

import numpy as np
import pytest

from comet.analysis.detectors import liquid_phase
from comet.core.types import Run
from comet.ingest import ingest

DATA = Path("tests/data")


def valve_open(run: Run) -> float:
    """First 0 -> 1 edge of the main valve state channel."""
    av = run.channels["valve_AV205"]
    return float(av.times[np.flatnonzero(np.diff(av.values) == 1)[0] + 1])


def test_qret_hf4_depletion_matches_hf_analysis_tools():
    run = ingest(DATA / "hot-fire-2026-07-11.yaml")
    depletion = liquid_phase(run.channel("chamber_pressure")).end - valve_open(run)
    assert depletion == pytest.approx(3.60, abs=0.05)


@pytest.mark.parametrize(
    ("descriptor", "onset_truth"),
    [("mcgill-hf4-2022.yaml", 6.164), ("mcgill-hf5-2022.yaml", 5.272)],
)
def test_mcgill_depletion_follows_onset_of_drop(descriptor, onset_truth):
    run = ingest(DATA / descriptor)
    depletion = liquid_phase(run.channel("chamber_pressure")).end  # t = 0 is valve open
    assert onset_truth - 0.05 <= depletion <= onset_truth + 0.35


def test_waterloo_tank_pressure_depletion_near_mass_flow_collapse():
    run = ingest(DATA / "waterloo-stf-2018.yaml")
    depletion = liquid_phase(run.channel("tank_pressure")).end
    assert depletion == pytest.approx(10.0, abs=1.0)


def test_waterloo_chamber_pressure_is_refused_not_guessed():
    """P_CC rises through the burn; the detector must refuse, not return a time."""
    run = ingest(DATA / "waterloo-stf-2018.yaml")
    with pytest.raises(ValueError):
        liquid_phase(run.channel("chamber_pressure"))
