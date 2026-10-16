"""Multi-zone thermal plant built on the TCLab energy-balance model.

Each zone is a heater + sensor pair (as on the TCLab board). Zones are arranged
in a chain and exchange heat with their neighbours by convection and radiation.
N=2 reproduces the TCLab two-heater board; N=4 is our multi-zone "furnace" case.

The same class is used for the "true" plant (with parameter mismatch, sensor
noise and injected faults) and for the digital twin (nominal or calibrated
parameters), so the twin is an executable copy of the plant physics.

Reference model: TCLab second-order energy balance (Hedengren et al.),
    m*Cp*dTH/dt = U*A*(Ta-TH) + eps*sigma*A*(Ta^4-TH^4)
                  + sum_nbr [U*As*(Tj-TH) + eps*sigma*As*(Tj^4-TH^4)] + alpha*Q
    dTC/dt      = (TH - TC) / tau_s
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

import numpy as np

SIGMA = 5.67e-8  # Stefan-Boltzmann constant, W/m^2/K^4
KELVIN = 273.15


@dataclass
class ThermalParams:
    """Physical parameters of an N-zone plant. Per-zone values are arrays."""

    n_zones: int = 2
    Ta: float = 23.0  # ambient temperature, degC
    m: float = 0.004  # heater+sensor mass, kg
    Cp: float = 500.0  # heat capacity, J/kg/K
    A: float = 12e-4  # exposed surface area per zone, m^2
    As: float = 2e-4  # area between neighbouring zones, m^2
    eps: float = 0.9  # emissivity
    U: np.ndarray = None  # heat transfer coefficient per zone, W/m^2/K
    alpha: np.ndarray = None  # heater gain per zone, W per % output
    tau_s: np.ndarray = None  # sensor lag per zone, s

    def __post_init__(self):
        n = self.n_zones
        if self.U is None:
            self.U = np.full(n, 10.0)
        if self.alpha is None:
            # TCLab: heater 1 = 0.01 W/%, heater 2 = 0.0075 W/%; alternate for N>2
            self.alpha = np.array([0.01 if i % 2 == 0 else 0.0075 for i in range(n)])
        if self.tau_s is None:
            self.tau_s = np.full(n, 12.0)
        self.U = np.asarray(self.U, dtype=float)
        self.alpha = np.asarray(self.alpha, dtype=float)
        self.tau_s = np.asarray(self.tau_s, dtype=float)

    def copy(self) -> "ThermalParams":
        return copy.deepcopy(self)

    def perturbed(self, rng: np.random.Generator, level: float) -> "ThermalParams":
        """Return a copy with multiplicative mismatch U(1-level, 1+level) on uncertain parameters."""
        p = self.copy()
        if level <= 0:
            return p
        n = self.n_zones
        p.U = p.U * rng.uniform(1 - level, 1 + level, n)
        p.alpha = p.alpha * rng.uniform(1 - level, 1 + level, n)
        p.tau_s = p.tau_s * rng.uniform(1 - level, 1 + level, n)
        p.m = p.m * rng.uniform(1 - level / 2, 1 + level / 2)
        return p


@dataclass
class FaultState:
    """Active fault effects applied inside the plant step (all identity when healthy)."""

    alpha_scale: np.ndarray  # multiplicative heater gain (actuator degradation)
    U_scale: np.ndarray  # multiplicative heat-loss coefficient (process fault)
    sensor_bias: np.ndarray  # additive measurement bias, degC (sensor fault)
    stuck_value: np.ndarray  # NaN = healthy, else actuator stuck at this % output

    @classmethod
    def healthy(cls, n: int) -> "FaultState":
        return cls(np.ones(n), np.ones(n), np.zeros(n), np.full(n, np.nan))

    def copy(self) -> "FaultState":
        return copy.deepcopy(self)


@dataclass
class PlantState:
    TH: np.ndarray  # heater (true) temperatures, degC
    TC: np.ndarray  # sensor-node temperatures, degC

    def copy(self) -> "PlantState":
        return PlantState(self.TH.copy(), self.TC.copy())


class ThermalPlant:
    """Discrete-time simulator (RK4) of the multi-zone thermal plant."""

    def __init__(self, params: ThermalParams, dt: float = 1.0, noise_std: float = 0.0,
                 rng: np.random.Generator | None = None, master_power: bool = True):
        self.p = params
        self.n = params.n_zones
        self.dt = dt
        self.noise_std = noise_std
        self.rng = rng or np.random.default_rng(0)
        self.fault = FaultState.healthy(self.n)
        self.master_power = master_power  # hard interlock: False cuts all heaters
        self.state = PlantState(np.full(self.n, params.Ta), np.full(self.n, params.Ta))
        self.t = 0.0

    # ---- physics -------------------------------------------------------
    def _derivatives(self, TH: np.ndarray, TC: np.ndarray, Q: np.ndarray):
        p, f = self.p, self.fault
        Ta_K = p.Ta + KELVIN
        TH_K = TH + KELVIN
        U = p.U * f.U_scale
        conv = U * p.A * (p.Ta - TH)
        rad = p.eps * SIGMA * p.A * (Ta_K**4 - TH_K**4)
        inter = np.zeros(self.n)
        for i in range(self.n - 1):  # chain coupling between neighbours i, i+1
            q = (U[i] + U[i + 1]) / 2 * p.As * (TH[i + 1] - TH[i]) \
                + p.eps * SIGMA * p.As * (TH_K[i + 1] ** 4 - TH_K[i] ** 4)
            inter[i] += q
            inter[i + 1] -= q
        heat = p.alpha * f.alpha_scale * Q
        dTH = (conv + rad + inter + heat) / (p.m * p.Cp)
        dTC = (TH - TC) / p.tau_s
        return dTH, dTC

    def effective_input(self, Q_cmd: np.ndarray) -> np.ndarray:
        Q = np.clip(np.asarray(Q_cmd, dtype=float), 0.0, 100.0)
        stuck = ~np.isnan(self.fault.stuck_value)
        Q = np.where(stuck, self.fault.stuck_value, Q)
        if not self.master_power:
            Q = np.zeros_like(Q)
        return Q

    def step(self, Q_cmd: np.ndarray) -> np.ndarray:
        """Advance one sample with commanded heater outputs (0-100 %). Returns measurement."""
        Q = self.effective_input(Q_cmd)
        TH, TC, h = self.state.TH, self.state.TC, self.dt
        k1 = self._derivatives(TH, TC, Q)
        k2 = self._derivatives(TH + h / 2 * k1[0], TC + h / 2 * k1[1], Q)
        k3 = self._derivatives(TH + h / 2 * k2[0], TC + h / 2 * k2[1], Q)
        k4 = self._derivatives(TH + h * k3[0], TC + h * k3[1], Q)
        self.state.TH = TH + h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
        self.state.TC = TC + h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
        self.t += h
        self.last_Q = Q
        return self.measure()

    def measure(self) -> np.ndarray:
        y = self.state.TC + self.fault.sensor_bias
        if self.noise_std > 0:
            y = y + self.rng.normal(0.0, self.noise_std, self.n)
        return np.round(y, 2)  # TCLab reports 0.01 degC resolution

    # ---- utilities -----------------------------------------------------
    def steady_state(self, Q: np.ndarray, iters: int = 4000) -> np.ndarray:
        """Steady-state heater temperatures for constant input (used by feasibility tools)."""
        sim = self.clone()
        sim.noise_std = 0.0
        for _ in range(iters):
            sim.step(Q)
        return sim.state.TH.copy()

    def clone(self) -> "ThermalPlant":
        c = ThermalPlant(self.p.copy(), self.dt, self.noise_std, np.random.default_rng(1), self.master_power)
        c.fault = self.fault.copy()
        c.state = self.state.copy()
        c.t = self.t
        return c
