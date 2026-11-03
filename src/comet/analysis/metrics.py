import numpy as np

from comet.core.plugins import metric
from comet.core.regions import before, crop, end_of, mean, value_at
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


@metric(unit="kg")
def oxidizer_mass_used(mass: TankMass, region: Region, settle: float = 2.0) -> float:
    """Tank mass lost over the region.

    Start mass is the mean over the `settle` seconds before the region, end mass
    is taken right at the end of the burn.
    """
    return mean(mass, before(region, settle)) - value_at(mass, end_of(mass, region))
