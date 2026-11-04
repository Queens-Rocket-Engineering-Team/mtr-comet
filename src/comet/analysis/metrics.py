import numpy as np

from comet.analysis.properties import n2o_saturated_density
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
    LiquidPhase,
    MotorConfig,
    PreInjectorPressure,
    Region,
    TankMass,
    TankPressure,
    Thrust,
)
from comet.core.units import PSI


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


@metric(unit="")
def discharge_coefficient(
    upstream: PreInjectorPressure,
    chamber: ChamberPressure,
    tank: TankPressure,
    mass: TankMass,
    region: Region,
    liquid: LiquidPhase,
    motor: MotorConfig,
    ambient_psi: float = 14.696,
    settle: float = 2.0,
) -> float:
    """Injector Cd: mass drained over the region divided by the ideal (Cd = 1) mass.

    Ideal flow is single-phase incompressible, area * sqrt(2 * density * pressure drop),
    with saturated N2O density at tank pressure: liquid until the liquid-phase region
    ends, vapour after.
    """
    measured = oxidizer_mass_used(mass, region, settle)
    drop = injector_pressure_drop(upstream, chamber, region)
    p = crop(tank, region)
    # Tank reads gauge; saturation properties need absolute pressure.
    density = n2o_saturated_density(
        (p.values + ambient_psi) * PSI, p.times <= liquid.end
    )
    ideal_flow = motor.injector.area * np.sqrt(
        2 * density * np.clip(values_at(drop, p.times) * PSI, 0, None)
    )
    return measured / float(np.trapezoid(ideal_flow, p.times))
