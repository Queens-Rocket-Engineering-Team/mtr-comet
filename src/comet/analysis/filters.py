from comet.core.types import Channel


def despike(ch: Channel, samples: int = 3) -> Channel:
    """Replace each value with the median of its `samples` nearest neighbours.

    Removes isolated spikes while keeping steps and ramps, which a moving average blurs.
    """
    from scipy.signal import medfilt  # lazy: slow import

    # kernel is in samples, not seconds, for single-sample glitches
    # revisit if spikes turn out to be time-based at high frequencies
    return Channel(ch.name, ch.times, medfilt(ch.values, samples), ch.unit, ch.tags)
