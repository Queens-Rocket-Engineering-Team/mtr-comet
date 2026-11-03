import comet.api
from comet.analysis.detectors import tank_pressure_drop


def test_inputs_reads_tag_from_annotation():
    assert comet.api.inputs(tank_pressure_drop) == {"p": "tank_pressure"}
