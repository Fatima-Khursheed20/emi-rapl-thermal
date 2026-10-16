"""Re-implementation of the base paper's agentic FTC workflow (Vyas et al., JPC 2026).

    fault report --> knowledge retrieval --> Planning Agent (target mode)
                 --> Action Agent (recovery parameters)
                 --> Simulation + deterministic Validation on the digital twin
                 --> pass: actuate | fail: structured reprompt (<= budget) | budget hit: fallback

Differences from the original are deliberate and documented in docs/base_paper_mapping.md
(knowledge graph in Python instead of GraphDB/SPARQL; thermal plant instead of CSTR/mixer).
"""
from __future__ import annotations

import json

from pydantic import ValidationError

from ..contracts import (DecisionTrace, FaultReport, Mode, PlanDecision, RecoveryAction, Snapshot,
                         ValidationResult, Violation)
from ..env.closed_loop import ClosedLoop
from ..knowledge import retrieve
from ..llm.client import extract_json
from ..llm.prompts import action_messages, planner_messages, reprompt_message
from ..tools.validator import Validator
from .fallback import fallback_action


def _parse(model_cls, text: str):
    try:
        return model_cls.model_validate(extract_json(text)), None
    except (ValueError, ValidationError, json.JSONDecodeError) as e:
        return None, str(e)[:300]


def _lost_zones(report: FaultReport) -> set[int]:
    return {report.zone} if (report.fault_kind or "").startswith("actuator_stuck") and report.zone is not None else set()


class BasePaperAgent:
    """Monitoring -> planning -> action synthesis -> simulation -> validation -> reprompting."""

    def __init__(self, llm, validator: Validator, reprompt_budget: int = 5, name: str | None = None):
        self.llm = llm
        self.validator = validator
        self.budget = reprompt_budget
        self.name = name or f"base_agent[{validator.twin.mode}]"

    def decide(self, snap: Snapshot, report: FaultReport, true_loop: ClosedLoop) -> DecisionTrace:
        tr = DecisionTrace(method=self.name, fault_report=report)
        kb = retrieve(report.fault_kind, report.zone, snap.n_zones)
        s, r = snap.model_dump(mode="json"), report.model_dump(mode="json")
        ctx = {"snapshot": snap, "fault_report": report}

        p_msgs = planner_messages(s, r, kb)
        plan, a_msgs, feedback = None, None, None
        while True:
            # ---- planning (re-run when the planner is responsible for the failure)
            if plan is None:
                resp = self.llm.complete("planner", p_msgs, ctx)
                tr.llm_calls.append(resp.record)
                plan, err = _parse(PlanDecision, resp.text)
                if plan is None:
                    vr = ValidationResult(passed=False, responsible="planner",
                                          violations=[Violation(check="parse", message=f"invalid planner JSON: {err}")])
                    if not self._reprompt(tr, vr, p_msgs, resp.text):
                        break
                    continue
                tr.plans.append(plan)
                a_msgs = action_messages(s, r, kb, plan.target_mode.value)
            # ---- action synthesis
            resp = self.llm.complete("action", a_msgs, {**ctx, "mode": plan.target_mode, "feedback": feedback})
            tr.llm_calls.append(resp.record)
            action, err = _parse(RecoveryAction, resp.text)
            if action is None:
                vr = ValidationResult(passed=False, responsible="action",
                                      violations=[Violation(check="parse", message=f"invalid action JSON: {err}")])
            else:
                if action.mode != plan.target_mode:
                    tr.notes.append(f"action mode {action.mode.value} overridden by plan {plan.target_mode.value}")
                    action.mode = plan.target_mode
                if action.mode == Mode.SAFE_SHUTDOWN:
                    action.shutdown = True
                tr.actions.append(action)
                vr = self.validator.validate(action, true_loop, report, _lost_zones(report))
            tr.validations.append(vr)
            if vr.passed:
                tr.applied_action = action
                return tr
            feedback = [v.model_dump() for v in vr.violations]
            target = p_msgs if vr.responsible == "planner" else a_msgs
            if not self._reprompt(tr, vr, target, resp.text):
                break
            if vr.responsible == "planner":
                plan = None  # re-plan with feedback appended to planner conversation
        # ---- reprompt budget exhausted: deterministic fallback (counts as failure)
        tr.used_fallback = True
        tr.applied_action = fallback_action(snap, report, self.validator, true_loop)
        return tr

    def _reprompt(self, tr: DecisionTrace, vr: ValidationResult, msgs: list[dict], previous: str) -> bool:
        if tr.reprompts >= self.budget:
            return False
        tr.reprompts += 1
        msgs.append({"role": "assistant", "content": previous or "(empty)"})
        msgs.append(reprompt_message([v.model_dump() for v in vr.violations], previous or "(empty)"))
        return True
