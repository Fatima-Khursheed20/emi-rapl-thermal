"""Deterministic rule-table recovery (non-agentic workflow baseline).

A fixed fault-type -> action mapping written the way a control engineer would
hard-code it, using *nominal* fault magnitudes because the true magnitude is not
observable from the fault label. No simulation, no verification, no adaptation.
"""
from __future__ import annotations

from ..contracts import FaultReport, Mode, RecoveryAction, Snapshot
from ..env.faults import NOMINAL_MAGNITUDE
from ..knowledge import CONSTRAINTS

T_FULL = {0: 71.0, 1: 62.0}  # nominal isolated steady state at 100 % (odd/even zones)


def _t_full(z: int) -> float:
    return T_FULL[z % 2]


def rule_mode(report: FaultReport, snap: Snapshot) -> Mode:
    return {
        "heater_degradation": Mode.DERATE,
        "heat_loss_increase": Mode.DERATE,
        "sensor_bias": Mode.SENSOR_CORRECTION,
        "local_insulation_loss": Mode.DERATE,
        "actuator_stuck_high": Mode.SAFE_SHUTDOWN,
    }.get(report.fault_kind or "", Mode.DERATE)


def rule_action(report: FaultReport, snap: Snapshot, mode: Mode | str | None = None,
                feedback: list[dict] | None = None) -> RecoveryAction:
    mode = Mode(mode) if mode else rule_mode(report, snap)
    kind, z, Ta = report.fault_kind, report.zone, snap.ambient_T
    sp = list(snap.setpoints)
    max_d = CONSTRAINTS["max_derate_degC"]
    act = RecoveryAction(mode=mode, rationale="rule table")
    if mode == Mode.SAFE_SHUTDOWN:
        act.shutdown = True
        return act
    if kind == "heater_degradation" and z is not None:
        reach = Ta + NOMINAL_MAGNITUDE[kind] * (_t_full(z) - Ta) * 0.9
        act.setpoints[z] = round(max(sp[z] - max_d, min(sp[z], reach)), 1)
    elif kind == "heat_loss_increase":
        for i in range(snap.n_zones):
            reach = Ta + (_t_full(i) - Ta) / NOMINAL_MAGNITUDE[kind] * 0.9
            act.setpoints[i] = round(max(sp[i] - max_d, min(sp[i], reach)), 1)
    elif kind == "sensor_bias" and z is not None:
        act.mode = Mode.SENSOR_CORRECTION
        act.sensor_offset[z] = -NOMINAL_MAGNITUDE[kind]
    elif kind == "local_insulation_loss" and z is not None:
        reach = Ta + (_t_full(z) - Ta) / NOMINAL_MAGNITUDE[kind] * 0.9
        act.setpoints[z] = round(max(sp[z] - max_d, min(sp[z], reach)), 1)
    # crude reaction to validator feedback (used only by the scripted test client)
    for v in feedback or []:
        vz = v.get("zone")
        if v.get("check") in ("regulation", "safety_envelope") and vz is not None:
            cur = act.setpoints.get(vz, sp[vz])
            act.setpoints[vz] = round(max(sp[vz] - max_d, cur - 3.0), 1)
    return act
