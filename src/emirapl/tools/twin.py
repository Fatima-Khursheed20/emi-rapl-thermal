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
Phase 2 constructs its observation-driven calibrated twin through CalibratedTwin
in agents.phase2, where the fitted state and covariance are available.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil, isfinite

import numpy as np

from ..contracts import FaultReport, RecoveryAction
from ..env.closed_loop import ClosedLoop
from ..env.faults import NOMINAL_MAGNITUDE, FaultSpec, apply_fault
from ..env.simulation import closed_loop
from ..env.thermal import FaultState, PlantState, ThermalParams, ThermalPlant


@dataclass
class Rollout:
    t: np.ndarray
    TH: np.ndarray  # true heater temps in the twin, (T, n)
    y: np.ndarray  # twin measurements
    u: np.ndarray  # heater outputs
    setpoints: np.ndarray
    hold: int = 0  # samples before the action takes effect


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
            raise NotImplementedError("construct CalibratedTwin with an observation-derived estimate")
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
    def rollout(loop: ClosedLoop, action: RecoveryAction | None, horizon_s: float, delay_s: float = 0.0) -> Rollout:
        """Simulate `horizon_s` after the action takes effect; current settings are held for `delay_s`
        first (the decision/actuation latency), because that is what the real plant experiences."""
        sim = loop.clone()
        dt = sim.plant.dt
        if not isfinite(horizon_s) or not isfinite(delay_s) or horizon_s <= 0 or delay_s < 0:
            raise ValueError("Rollout requires a finite positive horizon and nonnegative delay.")
        hold = ceil(delay_s / dt)
        steps = hold + ceil(horizon_s / dt)

        def settings(loop):
            return np.array([[z.setpoint, z.gains.Kc, z.gains.tauI, z.gains.tauD, z.q_max, z.bias, offset]
                             for z, offset in zip(loop.ctrl.loops, loop.sensor_offset)], dtype=float)

        initial = settings(sim)
        integral = np.array([z.integral for z in sim.ctrl.loops], dtype=float)
        previous = np.array([np.nan if z.prev_meas is None else z.prev_meas for z in sim.ctrl.loops], dtype=float)
        power_before = sim.plant.master_power
        if action is not None:
            sim.apply(action)
        changed = settings(sim)
        plant = sim.plant
        TH, Y, U = closed_loop(plant.state.TH, plant.state.TC, sim.y, dt, plant.physics(), plant.fault.stuck_value,
                               plant.fault.sensor_bias, initial, changed, integral, previous, power_before,
                               plant.master_power, hold, steps)
        return Rollout(np.arange(1, steps + 1) * dt, TH, Y, U, changed[:, 0].copy(), hold)
