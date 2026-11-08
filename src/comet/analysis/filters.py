from comet.core.types import Channel


def despike(ch: Channel, samples: int = 3) -> Channel:
    """Replace each value with the median of its `samples` nearest neighbours.

    Removes isolated spikes while keeping steps and ramps, which a moving average blurs.
    """
    from scipy.signal import medfilt  # lazy: slow import

    # kernel is in samples, not seconds, for single-sample glitches
    # revisit if spikes turn out to be time-based at high frequencies
    return Channel(ch.name, ch.times, medfilt(ch.values, samples), ch.unit, ch.tags)


def savitzky_golay(ch: Channel, window: int = 15, polyorder: int = 2) -> Channel:
    """Smooth by fitting a polynomial to each window of samples (Savitzky-Golay).

    Keeps peaks and slopes better than a moving average of the same width.
    `window` is the number of samples fitted at a time and must be odd so it is
    centered on a sample. `polyorder` is the polynomial degree and must be less
    than `window`. Both are in samples, not seconds.
    """
    from scipy.signal import savgol_filter  # lazy: slow import

    if window % 2 == 0:
        raise ValueError("window must be odd")
    if polyorder >= window:
        raise ValueError("polyorder must be less than window")

    return Channel(
        ch.name, ch.times, savgol_filter(ch.values, window, polyorder), ch.unit, ch.tags
    )
