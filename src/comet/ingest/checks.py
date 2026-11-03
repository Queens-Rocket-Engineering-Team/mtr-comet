import numpy as np

from comet.core.types import Channel, Fault, Region


def railed(ch: Channel, lo: float, hi: float) -> list[Fault]:
    """Samples at or beyond the sensor's physical range [lo, hi]."""
    idx = np.flatnonzero((ch.values <= lo) | (ch.values >= hi))
    if len(idx) == 0:
        return []
    region = Region("railed", float(ch.times[idx[0]]), float(ch.times[idx[-1]]))
    return [Fault(ch.name, "railed", region)]
