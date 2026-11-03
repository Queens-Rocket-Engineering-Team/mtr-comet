import numpy as np
import scipy

from comet.core.types import Channel, Region


def value_at(ch: Channel, t: float) -> float:
    """Interpolate the value of a sensor channel at a given time"""
    # Verify time exists in channel
    if not ch.times[0] <= t <= ch.times[-1]:
        raise ValueError(
            f"{ch.name}: t={t} is outside recorded data [{ch.times[0]}, {ch.times[-1]}]"
        )
    return float(np.interp(t, ch.times, ch.values))


def crop(ch: Channel, region: Region) -> Channel:
    """The channel restricted to the region.

    Interpolated samples are added at the region boundaries.
    """
    end = end_of(ch, region)
    lo = np.searchsorted(ch.times, region.start, side="right")
    hi = np.searchsorted(ch.times, end, side="left")
    times = np.concatenate(([region.start], ch.times[lo:hi], [end]))
    values = np.concatenate(
        ([value_at(ch, region.start)], ch.values[lo:hi], [value_at(ch, end)])
    )
    return Channel(ch.name, times, values, ch.unit, ch.tags)


def end_of(ch: Channel, region: Region) -> float:
    """The region's end, or the end of the data for an open region."""
    return region.end if region.end is not None else float(ch.times[-1])


def cumulative(ch: Channel, region: Region) -> Channel:
    """Running integral over the region, starting at 0 at region.start."""
    cropped = crop(ch, region)

    return Channel(
        ch.name,
        cropped.times,
        scipy.integrate.cumulative_trapezoid(cropped.values, cropped.times, initial=0),
        unit=f"{ch.unit}*s",
    )


def integrate(ch: Channel, region: Region) -> float:
    """Returns the integral of the sensor channel over the specified region"""
    return float(cumulative(ch, region).values[-1])


def mean(ch: Channel, region: Region) -> float:
    """Returns the time-weighted mean of the channel values over a region"""
    # For open regions, find the end
    end = end_of(ch, region)
    if end == region.start:
        # For zero-length regions, use the value at the given time
        return value_at(ch, region.start)
    return integrate(ch, region) / (end - region.start)


def before(region: Region, seconds: float) -> Region:
    """Returns the window before the start of the region for the specified interval"""
    return Region("window", region.start - seconds, region.start)


def after(region: Region, seconds: float) -> Region:
    """Returns the window after the end of the region for the specified interval"""
    if region.end is None:
        raise ValueError("region has no end")
    return Region("window", region.end, region.end + seconds)


def mean_rate(ch: Channel, window: float) -> Channel:
    """Rate of change averaged over `window` seconds centred on each sample.

    Equals the mean of the true derivative over the window. Independent of sample
    rate when window >> sample period. Same as `np.gradient` when window == 2*dt.
    Near the channel ends the window is clipped to the data, so it is shorter there.
    """
    t_lo = np.clip(ch.times - window / 2, ch.times[0], ch.times[-1])
    t_hi = np.clip(ch.times + window / 2, ch.times[0], ch.times[-1])
    lo = np.interp(t_lo, ch.times, ch.values)
    hi = np.interp(t_hi, ch.times, ch.values)
    return Channel(
        ch.name, ch.times, (hi - lo) / (t_hi - t_lo), f"{ch.unit}/s", ch.tags
    )
