"""Injector flow models. Plain functions over SI numbers or arrays, no channels."""

import numpy as np
from numpy.typing import ArrayLike, NDArray


def spi_mass_flow(
    area_m2: float,
    density_kg_m3: ArrayLike,
    pressure_drop_pa: ArrayLike,
    cd: float = 1.0,
) -> NDArray[np.float64]:
    """Single-phase incompressible flow in kg/s: cd * area * sqrt(2 * density * drop).

    `cd` is the discharge coefficient, the fraction of ideal flow the injector
    passes, so 1.0 gives the ideal flow. Density and pressure drop may be a single
    number or arrays of the same length, for a flow at one instant or over a
    time series. The result is always an array. A negative pressure drop gives
    zero flow rather than a complex number.
    """
    drop = np.clip(np.asarray(pressure_drop_pa, dtype=float), 0, None)
    return cd * area_m2 * np.sqrt(2 * np.asarray(density_kg_m3, dtype=float) * drop)
