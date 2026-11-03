import numpy as np

from comet.core.plugins import detector
from comet.core.regions import mean_rate
from comet.core.types import Channel, Region, TankMass, TankPressure


@detector(kind="cold_flow")
def tank_pressure_drop(
    p: TankPressure, rate_threshold: float = 50.0, window: float = 1.0
) -> Region:
    """Interval where tank pressure falls faster than `rate_threshold`."""
    return _falling_interval(p, rate_threshold, window, "cold_flow")


@detector(kind="cold_flow")
def tank_mass_drop(
    m: TankMass, rate_threshold: float = 0.5, window: float = 1.0
) -> Region:
    """Interval where tank mass falls faster than `rate_threshold` (kg/s)."""
    return _falling_interval(m, rate_threshold, window, "cold_flow")


def _falling_interval(
    ch: Channel, rate_threshold: float, window: float, kind: str
) -> Region:
    """Shared helper. Returns the region when a channel falls faster than
    `rate_threshold`"""
    idx = np.flatnonzero(mean_rate(ch, window).values < -rate_threshold)
    if len(idx) == 0:
        raise ValueError(
            f"{ch.name}: never falls faster than {rate_threshold} {ch.unit}/s"
        )
    return Region(kind, float(ch.times[idx[0]]), float(ch.times[idx[-1]]))
