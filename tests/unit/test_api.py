import pytest

import comet.api
from comet.analysis.detectors import tank_pressure_drop
from comet.analysis.metrics import oxidizer_mass_used
from comet.core.plugins import metric
from comet.core.types import Region


def test_inputs_reads_tag_from_annotation():
    assert comet.api.channel_inputs(tank_pressure_drop) == {"p": "tank_pressure"}
    assert comet.api.region_inputs(tank_pressure_drop) == {}


def test_region_inputs_list_kinds_in_priority_order():
    assert comet.api.region_inputs(oxidizer_mass_used) == {
        "region": ["burn", "cold_flow"]
    }


def test_metric_with_untyped_region_is_refused():
    with pytest.raises(TypeError, match="typed region"):

        @metric(unit="")
        def bad(region: Region) -> float:
            return 0.0
