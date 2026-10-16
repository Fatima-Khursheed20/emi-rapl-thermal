"""Non-agentic and single-call baselines sharing the `decide(snapshot, report, loop)` interface."""
from __future__ import annotations

import numpy as np
from scipy.optimize import differential_evolution

from ..contracts import DecisionTrace, FaultReport, Mode, RecoveryAction, Snapshot, ZoneGains
from ..env.closed_loop import ClosedLoop
from ..knowledge import CONSTRAINTS, retrieve
from ..llm.client import extract_json
from ..llm.prompts import single_call_messages
from ..tools.twin import DigitalTwin
from ..tools.validator import Validator
from .rules import rule_action


class NoRecovery:
    """B0: keep the original PI loops untouched (fault-agnostic control)."""

    name = "no_recovery"

    def decide(self, snap: Snapshot, report: FaultReport, loop: ClosedLoop) -> DecisionTrace:
        return DecisionTrace(method=self.name, fault_report=report, notes=["no action"])


class RuleTable:
    """B1: deterministic fault-type -> action table with nominal magnitudes, no verification."""

    name = "rule_table"

    def decide(self, snap: Snapshot, report: FaultReport, loop: ClosedLoop) -> DecisionTrace:
        act = rule_action(report, snap)
        return DecisionTrace(method=self.name, fault_report=report, actions=[act], applied_action=act)


class SingleCallLLM:
    """B2: one LLM call proposes mode + parameters; applied without simulation or validation."""

    def __init__(self, llm):
        self.llm = llm
        self.name = "single_llm"

    def decide(self, snap: Snapshot, report: FaultReport, loop: ClosedLoop) -> DecisionTrace:
        tr = DecisionTrace(method=self.name, fault_report=report)
        kb = retrieve(report.fault_kind, report.zone, snap.n_zones)
        msgs = single_call_messages(snap.model_dump(mode="json"), report.model_dump(mode="json"), kb)
        resp = self.llm.complete("single", msgs, {"snapshot": snap, "fault_report": report})
        tr.llm_calls.append(resp.record)
        try:
            act = RecoveryAction.model_validate(extract_json(resp.text))
            if act.mode == Mode.SAFE_SHUTDOWN:
                act.shutdown = True
            # clip to hard actuator ranges only (no physics check)
            act.setpoints = {z: float(np.clip(v, *CONSTRAINTS["setpoint_range"])) for z, v in act.setpoints.items()
                             if 0 <= int(z) < snap.n_zones}
            tr.actions.append(act)
            tr.applied_action = act
        except Exception as e:  # unparseable reply -> nothing applied
            tr.notes.append(f"parse failure: {str(e)[:200]}")
        return tr


class DERetune:
    """B3: differential-evolution search over recovery parameters on the digital twin (no LLM).

    Represents the seed project's NN/DE tuning line: an optimiser with a model but no reasoning.
    Variables: setpoint derate of affected zones, PI gains of affected zones, sensor offset.
    """

    def __init__(self, validator: Validator, maxiter: int = 8, popsize: int = 6, horizon_s: float = 1200.0, seed: int = 0):
        self.v = validator
        self.maxiter, self.popsize, self.horizon_s, self.seed = maxiter, popsize, horizon_s, seed
        self.name = f"de_retune[{validator.twin.mode}]"

    def decide(self, snap: Snapshot, report: FaultReport, loop: ClosedLoop) -> DecisionTrace:
        tr = DecisionTrace(method=self.name, fault_report=report)
        n = snap.n_zones
        zones = list(range(n)) if report.fault_class == "process" or report.zone is None else [report.zone]
        lost = {report.zone} if (report.fault_kind or "").startswith("actuator_stuck") else set()
        twin_loop = self.v.twin.build(loop, report)
        limit, max_d = CONSTRAINTS["safety_limit_T"], CONSTRAINTS["max_derate_degC"]
        sensor = report.fault_class == "sensor"
        # x = [derate_z..., Kc_z..., tauI_z..., (offset)]
        bounds = [(0, max_d)] * len(zones) + [(1.0, 12.0)] * len(zones) + [(40.0, 400.0)] * len(zones)
        if sensor:
            bounds.append(tuple(CONSTRAINTS["sensor_offset_range"]))

        def to_action(x) -> RecoveryAction:
            k = len(zones)
            a = RecoveryAction(mode=Mode.SENSOR_CORRECTION if sensor else Mode.DERATE, rationale="DE optimum")
            for i, z in enumerate(zones):
                a.setpoints[z] = round(snap.setpoints[z] - float(x[i]), 2)
                a.gains[z] = ZoneGains(Kc=round(float(x[k + i]), 3), tauI=round(float(x[2 * k + i]), 1))
            if sensor:
                a.sensor_offset[report.zone] = round(float(x[-1]), 2)
            return a

        def cost(x) -> float:
            ro = DigitalTwin.rollout(twin_loop, to_action(x), self.horizon_s)
            tail = ro.TH[-300:]
            healthy = [z for z in range(n) if z not in lost]
            track = float(np.mean(np.abs(tail[:, healthy] - ro.setpoints[healthy])))
            excess = float(np.clip(ro.TH.max(axis=0) - limit, 0, None).sum())
            derate = float(np.sum(x[:len(zones)]))
            return track + 20.0 * excess + 0.15 * derate

        res = differential_evolution(cost, bounds, maxiter=self.maxiter, popsize=self.popsize, seed=self.seed,
                                     polish=False, tol=1e-3)
        best = to_action(res.x)
        tr.notes.append(f"DE evals={res.nfev} cost={res.fun:.3f}")
        ro = DigitalTwin.rollout(twin_loop, best, self.horizon_s)
        if ro.TH.max() > limit:  # no safe operating point found by the optimiser
            best = RecoveryAction(mode=Mode.SAFE_SHUTDOWN, shutdown=True, rationale="DE found no safe operating point")
        tr.actions.append(best)
        tr.applied_action = best
        return tr
