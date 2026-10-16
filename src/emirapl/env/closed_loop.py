"""Plant + PI controllers + sensor-offset correction, stepped together."""
from __future__ import annotations

import numpy as np

from ..contracts import RecoveryAction
from ..control.pid import MultiZoneController, PIDGains
from .thermal import ThermalPlant


class ClosedLoop:
    def __init__(self, plant: ThermalPlant, controller: MultiZoneController):
        self.plant = plant
        self.ctrl = controller
        self.n = plant.n
        self.sensor_offset = np.zeros(self.n)
        self.y = plant.measure()
        self.u = np.zeros(self.n)

    def step(self) -> np.ndarray:
        y_corr = self.y + self.sensor_offset
        self.u = self.ctrl.compute(y_corr, self.plant.dt)
        self.y = self.plant.step(self.u)
        return self.y

    def apply(self, action: RecoveryAction) -> None:
        """Apply a validated recovery action to the controllers / interlock."""
        if action.shutdown:
            self.plant.master_power = False
        for z, sp in action.setpoints.items():
            self.ctrl.loops[int(z)].setpoint = float(sp)
        for z, g in action.gains.items():
            loop = self.ctrl.loops[int(z)]
            loop.gains = PIDGains(Kc=float(g.Kc), tauI=float(g.tauI))
        for z, q in action.q_max.items():
            self.ctrl.loops[int(z)].q_max = float(q)
        for z, off in action.sensor_offset.items():
            self.sensor_offset[int(z)] = float(off)

    def clone(self, plant: ThermalPlant | None = None) -> "ClosedLoop":
        c = ClosedLoop.__new__(ClosedLoop)
        c.plant = plant if plant is not None else self.plant.clone()
        c.ctrl = self.ctrl.clone()
        c.n = self.n
        c.sensor_offset = self.sensor_offset.copy()
        c.y = self.y.copy()
        c.u = self.u.copy()
        return c
