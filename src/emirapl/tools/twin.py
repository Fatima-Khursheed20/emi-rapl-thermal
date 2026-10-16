"""Digital Process Plant Twin (DPPT) service: simulation tool used before actuation.

Twin modes
----------
matched : exact copy of the true plant, including hidden parameter values and the
          exact injected fault. This is the evaluation assumption of the base paper
          (Vyas et al., JPC 2026: "the DPPT ... is identical to the model generating
          the simulated plant behavior and uses the same injected fault configuration").
nominal : what is realistically available: nominal parameters, the *reported* fault
          type/zone with an assumed nominal magnitude, and a state reconstructed from
          measurements. This exposes the base paper's matched-model gap.
calibrated : reserved for the proposed system (Gap 1) - parameters and uncertainty
          from online adaptive-EKF calibration. Implemented in Phase 2.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..contracts import FaultReport, RecoveryAction
from ..env.closed_loop import ClosedLoop
from ..env.faults import NOMINAL_MAGNITUDE, FaultSpec, apply_fault
from ..env.thermal import FaultState, PlantState, ThermalParams, ThermalPlant


@dataclass
class Rollout:
    t: np.ndarray
    TH: np.ndarray  # true heater temps in the twin, (T, n)
    y: np.ndarray  # twin measurements
    u: np.ndarray  # heater outputs
    setpoints: np.ndarray


class DigitalTwin:
    def __init__(self, mode: str, nominal_params: ThermalParams, dt: float = 1.0):
        if mode not in ("matched", "nominal", "calibrated"):
            raise ValueError(mode)
        self.mode = mode
        self.nominal = nominal_params
        self.dt = dt

    def build(self, true_loop: ClosedLoop, report: FaultReport) -> ClosedLoop:
        """Create the twin closed loop at the current time."""
        if self.mode == "matched":
            return true_loop.clone()  # oracle copy: same params, same fault, same hidden state
        if self.mode == "calibrated":
            raise NotImplementedError("calibrated twin (Gap 1) is implemented in Phase 2")
        plant = ThermalPlant(self.nominal.copy(), self.dt, noise_std=0.0)
        plant.fault = FaultState.healthy(plant.n)
        if report.fault_kind is not None and report.zone is not None:
            apply_fault(plant.fault, FaultSpec(report.fault_kind, report.zone,
                                               NOMINAL_MAGNITUDE[report.fault_kind], 0.0))
        plant.master_power = true_loop.plant.master_power
        # state reconstruction from (bias-assumed) measurements: TH ~ TC ~ y - bias
        y_true_est = true_loop.y - plant.fault.sensor_bias
        plant.state = PlantState(y_true_est.copy(), y_true_est.copy())
        twin = true_loop.clone(plant=plant)
        twin.y = plant.measure()
        return twin

    @staticmethod
    def rollout(loop: ClosedLoop, action: RecoveryAction | None, horizon_s: float) -> Rollout:
        sim = loop.clone()
        sim.plant.noise_std = 0.0
        if action is not None:
            sim.apply(action)
        steps = int(horizon_s / sim.plant.dt)
        TH, Y, U = np.zeros((steps, sim.n)), np.zeros((steps, sim.n)), np.zeros((steps, sim.n))
        for k in range(steps):
            Y[k] = sim.step()
            TH[k] = sim.plant.state.TH
            U[k] = sim.plant.last_Q
        sps = np.array([l.setpoint for l in sim.ctrl.loops])
        return Rollout(np.arange(steps) * sim.plant.dt, TH, Y, U, sps)
