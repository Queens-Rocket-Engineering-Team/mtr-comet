from pathlib import Path

import pytest

from comet.analysis.detectors import thrust_above
from comet.analysis.metrics import oxidizer_mass_used
from comet.ingest import ingest


def test_hotfire_mass_used_from_csv():
    run = ingest(Path("tests/data/hot-fire-2026-07-11.yaml"))

    thrust = run.channel("thrust")

    burn = thrust_above(thrust)

    assert burn.kind == "burn"
    assert oxidizer_mass_used(run.channel("tank_mass"), burn) == pytest.approx(
        7.5, abs=0.2
    )
