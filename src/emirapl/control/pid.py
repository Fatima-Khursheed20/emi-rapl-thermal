"""Discrete PI(D) controllers with anti-windup, one loop per zone."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np


@dataclass
class PIDGains:
    Kc: float = 4.0  # % output per degC
    tauI: float = 120.0  # s
    tauD: float = 0.0  # s

    def as_dict(self) -> dict:
        return {"Kc": self.Kc, "tauI": self.tauI, "tauD": self.tauD}


@dataclass
class ZoneLoop:
    gains: PIDGains = field(default_factory=PIDGains)
    setpoint: float = 45.0
    q_max: float = 100.0  # output limit (derating knob), %
    integral: float = 0.0
    prev_meas: float | None = None
    bias: float = 0.0

    def update(self, meas: float, dt: float) -> float:
        g = self.gains
        e = self.setpoint - meas
        d = 0.0 if self.prev_meas is None else -(meas - self.prev_meas) / dt
        self.prev_meas = meas
        u_unsat = self.bias + g.Kc * e + (g.Kc / g.tauI) * self.integral + g.Kc * g.tauD * d
        u = float(np.clip(u_unsat, 0.0, self.q_max))
        # conditional integration (anti-windup): only integrate when not pushing further into saturation
        if not ((u_unsat > self.q_max and e > 0) or (u_unsat < 0.0 and e < 0)):
            self.integral += e * dt
        return u


class MultiZoneController:
    """Bank of independent zone loops plus an optional measurement override per zone.

    `substitute` lets a recovery action replace a faulty sensor reading with an
    estimate (e.g. from the digital twin); the controller then regulates the estimate.
    """

    def __init__(self, n_zones: int, setpoints, gains: PIDGains | None = None):
        self.loops = [ZoneLoop(gains=PIDGains(**(gains or PIDGains()).as_dict()), setpoint=float(sp))
                      for sp in setpoints]
        self.n = n_zones
        self.substitute = np.zeros(n_zones, dtype=bool)

    def compute(self, meas: np.ndarray, dt: float, estimate: np.ndarray | None = None) -> np.ndarray:
        y = meas.copy()
        if estimate is not None and self.substitute.any():
            y[self.substitute] = estimate[self.substitute]
        return np.array([loop.update(float(y[i]), dt) for i, loop in enumerate(self.loops)])

    def snapshot(self) -> dict:
        return {
            "setpoints": [round(l.setpoint, 2) for l in self.loops],
            "gains": [l.gains.as_dict() for l in self.loops],
            "q_max": [l.q_max for l in self.loops],
            "sensor_substitution": [bool(s) for s in self.substitute],
        }

    def clone(self) -> "MultiZoneController":
        import copy
        return copy.deepcopy(self)
