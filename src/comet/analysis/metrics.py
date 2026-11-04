import numpy as np

from comet.analysis.filters import despike
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
    Burn,
    ChamberPressure,
    Channel,
    LiquidPhase,
    MotorConfig,
    OxidizerFlow,
    PreInjectorPressure,
    TankMass,
    TankPressure,
    Thrust,
)
from comet.core.units import PSI


@metric(unit="kg/s")
def oxidizer_mass_flow(mass: TankMass, region: OxidizerFlow) -> Channel:
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
def oxidizer_mass_used(
    mass: TankMass, region: OxidizerFlow, settle: float = 2.0
) -> float:
    """Tank mass lost over the region.

    Start mass is the mean over the `settle` seconds before the region, end mass
    is taken right at the end of the burn.
    """
    return mean(mass, before(region, settle)) - value_at(mass, end_of(mass, region))


@metric(unit="N*s")
def total_impulse(thrust: Thrust, region: Burn) -> float:
    """Integral of thrust over the region."""
    return integrate(thrust, region)


@metric(unit="s")
def burn_time(region: Burn) -> float:
    """Length of the region."""
    if region.end is None:
        raise ValueError("region has no end")
    return region.end - region.start


@metric(unit="psi")
def injector_pressure_drop(
    upstream: PreInjectorPressure, chamber: ChamberPressure, region: OxidizerFlow
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
    region: OxidizerFlow,
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


@metric(unit="")
def thrust_coefficient(
    thrust: Thrust,
    chamber: ChamberPressure,
    region: Burn,
    motor: MotorConfig,
    ambient_psi: float = 14.696,
    settle: float = 2.0,
    min_chamber_psi: float = 30.0,
) -> Channel:
    """Thrust coefficient: thrust over absolute chamber pressure times throat area.

    Chamber pressure on the throat area is the force before the nozzle does anything;
    the coefficient is how much the nozzle multiplies it. It depends only on the
    nozzle's expansion ratio and the gas, so a value well below the ideal for that
    ratio points at the thrust or pressure measurement, or at the throat size.
    """
    # Tare thrust using the zero-thrust window before the burn
    tare = mean(thrust, before(region, settle))
    dt = float(np.median(np.diff(thrust.times)))
    force = crop(despike(thrust, samples=max(3, round(0.2 / dt) | 1)), region)
    pressure = values_at(chamber, force.times)

    # Near zero pressure the ratio is meaningless. Drop those samples rather
    # than divide, so the series may start after the region does.
    kept = pressure > min_chamber_psi
    cf = (force.values[kept] - tare) / (
        (pressure[kept] + ambient_psi) * PSI * motor.nozzle.throat_area
    )
    return Channel("thrust_coefficient", force.times[kept], cf, unit="")
