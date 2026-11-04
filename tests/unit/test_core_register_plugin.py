import numpy as np
import pytest

from comet.core.plugins import metric
from comet.core.regions import integrate
from comet.core.types import Burn, Channel, Region, Thrust


def test_register_metric():
    @metric(unit="N*s")
    def total_impulse(thrust: Thrust, region: Burn) -> float:
        return integrate(thrust, region)

    thrust: Thrust = Channel(
        name="LCThrust", times=np.array([1, 2, 3]), values=np.array([4, 6, 8]), unit="N"
    )
    region: Region = Region(kind="burn", start=1, end=3)

    assert total_impulse.__comet_plugin__.name == "metric/total_impulse"  # type: ignore[ty:unresolved-attribute]
    assert total_impulse(thrust, region) == pytest.approx(12.0)
