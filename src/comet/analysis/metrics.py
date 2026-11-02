import numpy as np

from comet.core.plugins import metric
from comet.core.regions import crop
from comet.core.types import Channel, Region, TankMass


@metric(unit="kg/s")
def oxidizer_mass_flow(mass: TankMass, region: Region) -> Channel:
    """Rate of oxidizer leaving the tank over the region, as -d(mass)/dt.

    Positive during flow.
    """
    m = crop(mass, region)
    return Channel(
        "oxidizer_mass_flow",
        m.times,
        -np.gradient(m.values, m.times),
        unit=f"{m.unit}/s",
    )
