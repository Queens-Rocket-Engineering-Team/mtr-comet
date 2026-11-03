import pytest

from comet.analysis.detectors import tank_pressure_drop
from comet.analysis.filters import despike
from comet.analysis.metrics import oxidizer_mass_flow
from comet.core.regions import mean
from comet.ingest.adapter import QRETCsvAdapter


def test_cold_flow_mass_flow_from_csv():
    adapter = QRETCsvAdapter()

    run = adapter.ingest(
        "tests/data/cold-flow-2026-03-06-slice.csv",
        tags={"PTRun": ["tank_pressure"], "LCFill": ["tank_mass"]},
    )

    pressure = run.channel("tank_pressure")
    mass = despike(run.channel("tank_mass"))

    flow_region = tank_pressure_drop(pressure)
    flow_rate = oxidizer_mass_flow(mass, flow_region)

    avg_mass_flow = mean(flow_rate, flow_region)

    assert flow_region.kind == "cold_flow"
    assert avg_mass_flow == pytest.approx(1.6, abs=0.05)
