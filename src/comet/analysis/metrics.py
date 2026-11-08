import numpy as np

from comet.analysis.filters import despike
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
from comet.core.units import PA_PER_PSI
from comet.models.injector import spi_mass_flow
from comet.models.nitrous import n2o_saturated_density


@metric(unit="kg/s")
def oxidizer_mass_flow(mass: TankMass, region: OxidizerFlow) -> Channel:
    """Rate of oxidizer leaving the tank over the region, as -d(mass)/dt.

    Positive during flow.
    """
    m = crop(mass, region)
    # Mass falls as oxidizer leaves, so the flow out is minus the slope. This is a
    # per-sample derivative: integrating it does not recover the mass change exactly,
    # so use oxidizer_mass_used for totals.
    flow_out = -np.gradient(m.values, m.times)
    return Channel("oxidizer_mass_flow", m.times, flow_out, unit=f"{m.unit}/s")


@metric(unit="kg")
def oxidizer_mass_used(
    mass: TankMass, region: OxidizerFlow, settle: float = 2.0
) -> float:
    """Tank mass lost over the region.

    Start mass is the mean over the `settle` seconds before the region, end mass
    is taken right at the end of the burn.
    """
    # The start is averaged over a quiet window because the reading is disturbed when
    # flow begins. The end is a single value because the tank may keep emptying after.
    start_mass = mean(mass, before(region, settle))
    end_mass = value_at(mass, end_of(mass, region))
    return start_mass - end_mass


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

    # The tank transducer reads gauge, and saturation properties need absolute.
    is_liquid = p.times <= liquid.end
    density = n2o_saturated_density((p.values + ambient_psi) * PA_PER_PSI, is_liquid)
    # The model is linear in cd, so cd=1 gives the flow an ideal injector would pass.
    # The real injector passed `measured`, and Cd is the ratio of the two masses.
    ideal_flow = spi_mass_flow(
        motor.injector.area, density, values_at(drop, p.times) * PA_PER_PSI, cd=1.0
    )
    ideal_mass = float(np.trapezoid(ideal_flow, p.times))
    return measured / ideal_mass


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

    Chamber pressure on the throat area is the force before the nozzle does anything.
    The coefficient is how much the nozzle multiplies it. It depends only on the
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
        (pressure[kept] + ambient_psi) * PA_PER_PSI * motor.nozzle.throat_area
    )
    return Channel("thrust_coefficient", force.times[kept], cf, unit="")
