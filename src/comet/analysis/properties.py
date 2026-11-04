import numpy as np
from CoolProp.CoolProp import PropsSI


def n2o_saturated_density(p_pa: np.ndarray, liquid: np.ndarray) -> np.ndarray:
    """Saturated N2O density at each pressure: liquid where `liquid`, else vapour."""
    p = np.maximum(p_pa, 1e5)
    return np.where(
        liquid,
        PropsSI("D", "P", p, "Q", 0, "NitrousOxide"),
        PropsSI("D", "P", p, "Q", 1, "NitrousOxide"),
    )
