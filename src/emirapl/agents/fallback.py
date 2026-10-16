"""Deterministic fallback policy used when no validated LLM plan is found in budget."""
from __future__ import annotations

from ..contracts import FaultReport, Mode, RecoveryAction, Snapshot
from ..env.closed_loop import ClosedLoop
from ..knowledge import CONSTRAINTS
from ..tools.twin import DigitalTwin


def fallback_action(snap: Snapshot, report: FaultReport, validator, true_loop: ClosedLoop) -> RecoveryAction:
    """Shut down if the twin predicts the current settings are unsafe, else derate affected zones by 10 degC."""
    twin_loop = validator.twin.build(true_loop, report)
    hold = DigitalTwin.rollout(twin_loop, None, validator.horizon_s, validator.delay_s)
    if hold.TH.max() > CONSTRAINTS["safety_limit_T"]:
        return RecoveryAction(mode=Mode.SAFE_SHUTDOWN, shutdown=True, rationale="fallback: unsafe hold")
    zones = range(snap.n_zones) if report.zone is None or report.fault_class == "process" else [report.zone]
    return RecoveryAction(mode=Mode.DERATE, rationale="fallback: conservative derate",
                          setpoints={z: round(snap.setpoints[z] - 10.0, 1) for z in zones})
