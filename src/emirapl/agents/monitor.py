"""Monitoring layer: residual-based fault detection (deterministic).

A nominal-model observer runs open loop beside the plant, fed with the same
commanded heater outputs. Residual statistics are learned from fault-free
operation (as the base paper derives mean/std/3-sigma references a priori) and
symptoms are raised when residuals, tracking error, saturation or temperature
leave their reference ranges for a persistent number of samples.

In the base-paper setting the fault *localisation* (kind + zone) is supplied by an
oracle, matching their assumption that localisation is out of scope.
"""
from __future__ import annotations

import numpy as np

from ..contracts import FaultReport
from ..env.faults import FaultSpec
from ..env.thermal import ThermalParams, ThermalPlant
from ..knowledge import FAULT_CLASS


class ResidualMonitor:
    def __init__(self, nominal: ThermalParams, calib_window=(900.0, 1500.0), persist_s: int = 20,
                 track_tol: float = 3.0, track_persist_s: int = 60, sat_persist_s: int = 120,
                 high_T: float = 57.0):
        self.obs = ThermalPlant(nominal.copy(), noise_std=0.0)
        self.n = nominal.n_zones
        self.calib_window = calib_window
        self.persist_s, self.track_tol = persist_s, track_tol
        self.track_persist_s, self.sat_persist_s, self.high_T = track_persist_s, sat_persist_s, high_T
        self._calib: list[np.ndarray] = []
        self.mu = np.zeros(self.n)
        self.thr = np.full(self.n, np.inf)
        self.cnt = {k: np.zeros(self.n, dtype=int) for k in ("res", "track", "sat", "high")}
        self.residual = np.zeros(self.n)
        self.report: FaultReport | None = None

    def update(self, t: float, y: np.ndarray, u_cmd: np.ndarray, setpoints: np.ndarray, q_max: np.ndarray) -> FaultReport | None:
        y_hat = self.obs.step(u_cmd)
        self.residual = y - y_hat
        lo, hi = self.calib_window
        if lo <= t < hi:
            self._calib.append(self.residual.copy())
            return None
        if t >= hi and np.isinf(self.thr).all() and self._calib:
            R = np.array(self._calib)
            self.mu = R.mean(axis=0)
            self.thr = np.maximum(1.5, 5.0 * R.std(axis=0))
        if t < hi or self.report is not None:
            return None
        cond = {
            "res": np.abs(self.residual - self.mu) > self.thr,
            "track": np.abs(y - setpoints) > self.track_tol,
            "sat": (u_cmd >= q_max - 0.5) & (setpoints - y > 0.5),
            "high": y > self.high_T,
        }
        need = {"res": self.persist_s, "track": self.track_persist_s, "sat": self.sat_persist_s, "high": 5}
        symptoms = []
        for k, c in cond.items():
            self.cnt[k] = np.where(c, self.cnt[k] + 1, 0)
            for z in np.where(self.cnt[k] >= need[k])[0]:
                symptoms.append(f"{ {'res': 'model_residual', 'track': 'tracking_loss', 'sat': 'heater_saturated', 'high': 'high_temperature'}[k] }_zone{z}")
        if symptoms:
            self.report = FaultReport(detected=True, t_detect_s=t, symptoms=symptoms)
            return self.report
        return None


def localise_oracle(report: FaultReport, spec: FaultSpec) -> FaultReport:
    """Base-paper assumption: monitoring supplies the correct fault kind and location."""
    r = report.model_copy()
    r.fault_kind = spec.kind
    r.zone = spec.zone
    r.fault_class = FAULT_CLASS[spec.kind]
    r.localisation_source = "oracle"
    return r
