"""Deterministic pre-execution validator (structure + twin-rollout checks).

Mirrors the base paper's validation stage: an action is executed on the plant only
if it passes (i) structural/admissibility checks against the knowledge base and
(ii) safety-envelope and dynamic-feasibility checks on a digital-twin rollout.
Violations are returned as structured, quantitative feedback for reprompting.
"""
from __future__ import annotations

import numpy as np

from ..contracts import FaultReport, Mode, RecoveryAction, ValidationResult, Violation
from ..env.closed_loop import ClosedLoop
from ..knowledge import ADMISSIBLE_MODES, CONSTRAINTS
from .twin import DigitalTwin


class Validator:
    def __init__(self, twin: DigitalTwin, nominal_setpoints, horizon_s: float = 1500.0,
                 settle_window_s: float = 300.0):
        self.twin = twin
        self.sp_nom = np.asarray(nominal_setpoints, dtype=float)
        self.horizon_s = horizon_s
        self.window = int(settle_window_s)

    # ------------------------------------------------------------------
    def structural(self, action: RecoveryAction, report: FaultReport, n: int) -> list[Violation]:
        v: list[Violation] = []
        c = CONSTRAINTS
        if action.mode not in ADMISSIBLE_MODES[report.fault_class]:
            v.append(Violation(check="mode_admissible", message=(
                f"mode {action.mode.value} is not admissible for a {report.fault_class} fault; "
                f"admissible: {[m.value for m in ADMISSIBLE_MODES[report.fault_class]]}")))
        if action.shutdown != (action.mode == Mode.SAFE_SHUTDOWN):
            v.append(Violation(check="mode_consistency", message="shutdown flag must be true iff mode is SAFE_SHUTDOWN"))
        for z in list(action.setpoints) + list(action.gains) + list(action.q_max) + list(action.sensor_offset):
            if not 0 <= int(z) < n:
                v.append(Violation(check="zone_exists", zone=int(z), message=f"zone {z} does not exist (n={n})"))
        for z, sp in action.setpoints.items():
            lo, hi = c["setpoint_range"]
            if not lo <= sp <= hi:
                v.append(Violation(check="setpoint_range", zone=int(z), value=sp, limit=hi,
                                   message=f"setpoint {sp:.1f} outside [{lo}, {hi}]"))
            if 0 <= int(z) < n and sp < self.sp_nom[int(z)] - c["max_derate_degC"]:
                v.append(Violation(check="max_derate", zone=int(z), value=sp,
                                   limit=self.sp_nom[int(z)] - c["max_derate_degC"],
                                   message=f"setpoint {sp:.1f} derates zone {z} by more than {c['max_derate_degC']} degC"))
        for z, g in action.gains.items():
            if not c["Kc_range"][0] <= g.Kc <= c["Kc_range"][1]:
                v.append(Violation(check="Kc_range", zone=int(z), value=g.Kc, message=f"Kc {g.Kc} outside {c['Kc_range']}"))
            if not c["tauI_range"][0] <= g.tauI <= c["tauI_range"][1]:
                v.append(Violation(check="tauI_range", zone=int(z), value=g.tauI, message=f"tauI {g.tauI} outside {c['tauI_range']}"))
        for z, q in action.q_max.items():
            if not 0.0 <= q <= 100.0:
                v.append(Violation(check="q_max_range", zone=int(z), value=q, message=f"q_max {q} outside [0, 100]"))
        for z, off in action.sensor_offset.items():
            lo, hi = c["sensor_offset_range"]
            if not lo <= off <= hi:
                v.append(Violation(check="offset_range", zone=int(z), value=off, message=f"offset {off} outside [{lo}, {hi}]"))
        return v

    # ------------------------------------------------------------------
    def validate(self, action: RecoveryAction, true_loop: ClosedLoop, report: FaultReport,
                 lost_zones: set[int] | None = None) -> ValidationResult:
        n = true_loop.n
        structural = self.structural(action, report, n)
        if structural:
            planner_err = any(v.check in ("mode_admissible",) for v in structural)
            return ValidationResult(passed=False, violations=structural,
                                    responsible="planner" if planner_err else "action")
        twin_loop = self.twin.build(true_loop, report)
        ro = DigitalTwin.rollout(twin_loop, action, self.horizon_s)
        limit = CONSTRAINTS["safety_limit_T"]
        band = CONSTRAINTS["regulation_band_degC"]
        v: list[Violation] = []
        max_T = ro.TH.max(axis=0)
        for z in range(n):
            if max_T[z] > limit:
                v.append(Violation(check="safety_envelope", zone=z, value=float(max_T[z]), limit=limit,
                                   message=f"twin predicts zone {z} reaches {max_T[z]:.1f} degC > limit {limit}"))
        track_err = np.full(n, np.nan)
        if not action.shutdown:
            lost = lost_zones or set()
            tail = ro.TH[-self.window:]
            for z in range(n):
                if z in lost:
                    continue
                track_err[z] = float(np.mean(np.abs(tail[:, z] - ro.setpoints[z])))
                if track_err[z] > band:
                    sat = float(np.mean(ro.u[-self.window:, z]))
                    v.append(Violation(check="regulation", zone=z, value=track_err[z], limit=band, message=(
                        f"twin predicts zone {z} misses setpoint {ro.setpoints[z]:.1f} by {track_err[z]:.2f} degC "
                        f"(mean heater output {sat:.0f}%) over the last {self.window}s")))
        else:
            # shutdown is only justified if continuing without it would be unsafe
            hold = DigitalTwin.rollout(twin_loop, None, self.horizon_s)
            hold_max = float(hold.TH.max())
            if hold_max <= limit:
                v.append(Violation(check="shutdown_justified", value=hold_max, limit=limit, message=(
                    f"shutdown not justified: twin predicts max {hold_max:.1f} degC <= {limit} under current settings")))
        predicted = {"max_T": [round(float(x), 2) for x in max_T],
                     "tracking_err": [None if np.isnan(e) else round(float(e), 3) for e in track_err]}
        return ValidationResult(passed=not v, violations=v, predicted=predicted,
                                responsible="none" if not v else (
                                    "planner" if any(x.check == "shutdown_justified" for x in v) else "action"))
