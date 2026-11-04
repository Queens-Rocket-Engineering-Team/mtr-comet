import numpy as np

from comet.core.types import Channel, Fault, Region


def railed(ch: Channel, lo: float, hi: float) -> list[Fault]:
    """Samples at or beyond the sensor's physical range [lo, hi]."""
    idx = np.flatnonzero((ch.values <= lo) | (ch.values >= hi))
    if len(idx) == 0:
        return []
    region = Region("railed", float(ch.times[idx[0]]), float(ch.times[idx[-1]]))
    return [Fault(ch.name, "railed", region)]


def glitch(ch: Channel, debounce: float) -> list[Fault]:
    """States held for less than `debounce` seconds on a state channel."""
    edges = np.flatnonzero(np.diff(ch.values) != 0) + 1
    starts, ends = edges[:-1], edges[1:]  # each state runs from one edge to the next
    return [
        Fault(
            ch.name, "glitch", Region("glitch", float(ch.times[s]), float(ch.times[e]))
        )
        for s, e in zip(starts, ends, strict=False)
        if ch.times[e] - ch.times[s] < debounce
    ]
