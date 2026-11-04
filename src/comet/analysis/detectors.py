import numpy as np

from comet.analysis.filters import despike
from comet.core.plugins import detector
from comet.core.regions import mean_rate
from comet.core.types import (
    ChamberPressure,
    Channel,
    Region,
    RunValve,
    TankMass,
    TankPressure,
    Thrust,
)


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


@detector(kind="burn")
def thrust_above(thrust: Thrust, threshold: float = 100.0) -> Region:
    """Interval where thrust exceeds threshold (N)."""
    idx = np.flatnonzero(thrust.values > threshold)
    if len(idx) == 0:
        raise ValueError(f"{thrust.name}: never exceeds {threshold} {thrust.unit}")
    return Region("burn", float(thrust.times[idx[0]]), float(thrust.times[idx[-1]]))


# Liquid Phase depletion
# Taken from hf_analysis_tools

# Pressure fall rate is measured between two samples this far apart.
LIQUID_DEPLETION_SLOPE_WINDOW = 0.5
# Ignore the first second after the burn starts, so start-up spikes are never mistaken
# for the pressure collapse.
LIQUID_DEPLETION_SEARCH_START = 1.0
# The stretch of burn, measured back from the steepest fall, that is assumed to still
# be liquid: from 1.6 s before it to 0.5 s before it. The "normal" pressure trend is
# fitted here.
LIQUID_DEPLETION_TREND_WINDOW = (1.6, 0.5)


@detector(kind="liquid_phase")
def liquid_phase(
    chamber: ChamberPressure,
    smoothing: float = 0.5,
    threshold: float = 0.05,
    min_level: float = 0.25,
) -> Region:
    """The part of the burn fed by liquid oxidizer, found from chamber pressure.

    `smoothing` is a median filter width in seconds, `threshold` the fraction below
    the pre-depletion trend that counts as depletion, `min_level` the fraction of
    peak pressure that counts as burning.
    """
    pressure = _smooth(chamber, smoothing)
    t, p = pressure.times, pressure.values

    # The burn starts when pressure first rises above a fraction of its peak.
    burning = p > min_level * p.max()
    onset = t[burning][0]

    # While liquid flows, pressure drifts down slowly. When the liquid runs out it
    # collapses. Find the collapse first: the steepest fall, ignoring start-up.
    steepest_fall = _steepest_fall(
        pressure, after=onset + LIQUID_DEPLETION_SEARCH_START, where=burning
    )

    # Fit a straight line to the slow drift just before the collapse. That is what
    # pressure "should" have done had the liquid lasted.
    trend = _linear_trend(
        pressure,
        start=steepest_fall - LIQUID_DEPLETION_TREND_WINDOW[0],
        end=steepest_fall - LIQUID_DEPLETION_TREND_WINDOW[1],
    )
    if trend is None:
        raise ValueError(f"{chamber.name}: burn too short to fit a liquid-phase trend")

    # Depletion is the first moment pressure falls a fraction below that line.
    departed = (t > steepest_fall - LIQUID_DEPLETION_TREND_WINDOW[0]) & (
        p < (1 - threshold) * trend
    )
    if not departed.any():
        raise ValueError(f"{chamber.name}: no liquid depletion found")
    depletion = t[departed][0]
    if depletion <= onset + LIQUID_DEPLETION_SEARCH_START:
        raise ValueError(f"{chamber.name}: no liquid depletion found")
    return Region("liquid_phase", float(onset), float(depletion))


def _smooth(ch: Channel, seconds: float) -> Channel:
    """Median filter of `seconds` width, converted to an odd sample count."""
    dt = float(np.median(np.diff(ch.times)))
    return despike(ch, samples=max(3, round(seconds / dt) | 1))


def _steepest_fall(ch: Channel, after: float, where: np.ndarray) -> float:
    """Time of the most negative rate of change after `after`, where `where` holds."""
    candidates = where & (ch.times > after)
    rate = mean_rate(ch, LIQUID_DEPLETION_SLOPE_WINDOW).values
    return float(ch.times[candidates][np.argmin(rate[candidates])])


def _linear_trend(ch: Channel, start: float, end: float) -> np.ndarray | None:
    """Straight line fitted to the channel between start and end, evaluated everywhere.

    None if fewer than ten samples fall in the window.
    """
    window = (ch.times >= start) & (ch.times <= end)
    if window.sum() <= 10:
        return None
    slope, intercept = np.polyfit(ch.times[window], ch.values[window], 1)
    return slope * ch.times + intercept


@detector(kind="run_valve_open")
def run_valve_open(valve: RunValve) -> Region:
    """From the first time the run valve opens to the last time it closes.

    Closures in between are inside the region: the valve is treated as open for
    the whole period it was commanded open.
    """
    opens = np.flatnonzero(np.diff(valve.values) == 1) + 1
    closes = np.flatnonzero(np.diff(valve.values) == -1) + 1
    if len(opens) == 0:
        raise ValueError(f"{valve.name}: never opens")
    end = (
        float(valve.times[closes[-1]])
        if len(closes) and closes[-1] > opens[-1]
        else None
    )
    return Region("run_valve_open", float(valve.times[opens[0]]), end)
