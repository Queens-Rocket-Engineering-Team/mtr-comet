import numpy as np

from comet.core.plugins import detector
from comet.core.types import Region, TankPressure


@detector(kind="cold_flow")
def tank_pressure_drop(p: TankPressure, rate_threshold: float = 50.0) -> Region:
    """Interval where tank pressure falls faster than rate_threshold."""
    falling = np.gradient(p.values, p.times) < -rate_threshold
    idx = np.flatnonzero(falling)
    return Region("cold_flow", p.times[idx[0]], p.times[idx[-1]])
