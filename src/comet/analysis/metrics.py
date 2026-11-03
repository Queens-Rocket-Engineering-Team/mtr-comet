import numpy as np

from comet.core.plugins import metric
from comet.core.regions import (
    before,
    crop,
    end_of,
    integrate,
    mean,
    value_at,
    values_at,
)
from comet.core.types import (
    ChamberPressure,
    Channel,
    PreInjectorPressure,
    Region,
    TankMass,
    Thrust,
)


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


@metric(unit="N*s")
def total_impulse(thrust: Thrust, region: Region) -> float:
    """Integral of thrust over the region."""
    return integrate(thrust, region)


@metric(unit="s")
def burn_time(region: Region) -> float:
    """Length of the region."""
    if region.end is None:
        raise ValueError("region has no end")
    return region.end - region.start


@metric(unit="psi")
def injector_pressure_drop(
    upstream: PreInjectorPressure, chamber: ChamberPressure, region: Region
) -> Channel:
    """Pressure drop across the injector over the region, upstream minus chamber."""
    if upstream.unit != chamber.unit:
        raise ValueError(f"units differ: {upstream.unit} != {chamber.unit}")
    up = crop(upstream, region)
    return Channel(
        "injector_pressure_drop",
        up.times,
        up.values - values_at(chamber, up.times),
        unit=up.unit,
    )
