"""Saturation properties of nitrous oxide. Pressures are absolute pascals."""

import functools

import numpy as np
from numpy.typing import ArrayLike, NDArray

# Stay below the critical point (7.245 MPa), where CoolProp becomes unreliable.
PRESSURE_FLOOR_PA = 1e5
PRESSURE_CEILING_PA = 7.0e6


@functools.cache
def _saturation_table() -> tuple[
    NDArray[np.float64], NDArray[np.float64], NDArray[np.float64]
]:
    """(pressure_pa, liquid density, vapour density) on a grid, built once."""
    from CoolProp.CoolProp import PropsSI  # lazy: slow import

    p = np.linspace(PRESSURE_FLOOR_PA, PRESSURE_CEILING_PA, 400)
    return (
        p,
        PropsSI("D", "P", p, "Q", 0, "NitrousOxide"),
        PropsSI("D", "P", p, "Q", 1, "NitrousOxide"),
    )


def n2o_saturated_density(
    pressure_pa: ArrayLike, liquid: ArrayLike
) -> NDArray[np.float64]:
    """Saturated density in kg/m^3 at each pressure: liquid where `liquid`, else vapour.

    `pressure_pa` may be a single number or an array. `liquid` is a bool, or a
    bool array of the same length, saying which phase to use at each point. The
    result is always an array. Values come from a cached table, and pressures
    outside the table are clamped to its edges.
    """
    grid, rho_liquid, rho_vapour = _saturation_table()
    p = np.clip(
        np.asarray(pressure_pa, dtype=float), PRESSURE_FLOOR_PA, PRESSURE_CEILING_PA
    )
    return np.where(
        np.asarray(liquid, dtype=bool),
        np.interp(p, grid, rho_liquid),
        np.interp(p, grid, rho_vapour),
    )
