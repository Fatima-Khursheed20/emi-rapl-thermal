"""One thermal safety rule shared by the validator and simulator evaluator."""
from dataclasses import dataclass

import numpy as np

from .knowledge import CONSTRAINTS

EXCURSION_TOL_DEGC = 0.5
EXCURSION_TOL_S = 60.0


@dataclass(frozen=True)
class ThermalSafety:
    peak_degC: float | None
    above_s: float
    valid: bool

    @property
    def violation(self):
        limit = CONSTRAINTS["safety_limit_T"]
        return (not self.valid or self.peak_degC > limit + EXCURSION_TOL_DEGC
                or self.above_s > EXCURSION_TOL_S)

    def as_dict(self):
        return {"peak_degC": self.peak_degC, "above_s": self.above_s, "valid": self.valid,
                "violation": self.violation}


def thermal_safety(temperatures, dt=1.0):
    values = np.asarray(temperatures)
    if not values.size:
        return None
    if not np.isfinite(values).all():
        return ThermalSafety(None, 0., False)
    limit = CONSTRAINTS["safety_limit_T"]
    return ThermalSafety(float(values.max()), float((values > limit).any(axis=1).sum() * dt), True)
