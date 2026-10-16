"""Prompt templates for the Planning and Action agents (base-paper roles)."""
from __future__ import annotations

import json

PLANNER_SYSTEM = """You are the Planning Agent of a supervisory fault-tolerant control system for a \
multi-zone electric thermal process (zones in a row, each with a heater, a temperature sensor and a PI loop).
A fault has been detected. Choose ONE target operating mode from the admissible modes in the knowledge context.
Prefer the least disruptive mode that keeps every true heater temperature below the safety limit and keeps the
healthy zones regulated. SAFE_SHUTDOWN stops production and is only acceptable when no operating mode can be safe.
Reply with a JSON object only: {"target_mode": "<MODE>", "rationale": "<one or two sentences>"}"""

ACTION_SYSTEM = """You are the Action Agent of a supervisory fault-tolerant control system for a multi-zone \
electric thermal process. Given the plant snapshot, the fault report, the knowledge context and the selected mode,
propose concrete recovery parameters. Only change what the mode requires. Zones are integers starting at 0.
Respect every range in the constraints. Reply with a JSON object only, using this schema:
{"mode": "<MODE>",
 "setpoints": {"<zone>": <degC>},
 "gains": {"<zone>": {"Kc": <%/degC>, "tauI": <s>}},
 "q_max": {"<zone>": <0-100 %>},
 "sensor_offset": {"<zone>": <degC added to the reading>},
 "shutdown": <true only for SAFE_SHUTDOWN>,
 "rationale": "<short justification with the numbers you used>"}"""

SINGLE_CALL_SYSTEM = """You supervise a multi-zone electric thermal process. A fault has been detected. In ONE reply,
choose a recovery mode and its parameters. Reply with a JSON object only, using this schema:
{"mode": "<MODE>", "setpoints": {"<zone>": <degC>}, "gains": {"<zone>": {"Kc": <num>, "tauI": <num>}},
 "q_max": {"<zone>": <0-100>}, "sensor_offset": {"<zone>": <degC>}, "shutdown": <bool>, "rationale": "<short>"}"""


def _dump(obj) -> str:
    return json.dumps(obj, indent=1, default=str)


def planner_messages(snapshot: dict, report: dict, knowledge: dict) -> list[dict]:
    user = (f"PLANT SNAPSHOT:\n{_dump(snapshot)}\n\nFAULT REPORT:\n{_dump(report)}\n\n"
            f"KNOWLEDGE CONTEXT:\n{_dump(knowledge)}\n\nSelect the target mode.")
    return [{"role": "system", "content": PLANNER_SYSTEM}, {"role": "user", "content": user}]


def action_messages(snapshot: dict, report: dict, knowledge: dict, mode: str) -> list[dict]:
    user = (f"PLANT SNAPSHOT:\n{_dump(snapshot)}\n\nFAULT REPORT:\n{_dump(report)}\n\n"
            f"KNOWLEDGE CONTEXT:\n{_dump(knowledge)}\n\nSELECTED MODE: {mode}\n\nPropose the recovery action.")
    return [{"role": "system", "content": ACTION_SYSTEM}, {"role": "user", "content": user}]


def single_call_messages(snapshot: dict, report: dict, knowledge: dict) -> list[dict]:
    user = (f"PLANT SNAPSHOT:\n{_dump(snapshot)}\n\nFAULT REPORT:\n{_dump(report)}\n\n"
            f"KNOWLEDGE CONTEXT:\n{_dump(knowledge)}")
    return [{"role": "system", "content": SINGLE_CALL_SYSTEM}, {"role": "user", "content": user}]


def reprompt_message(violations: list[dict], previous: str) -> dict:
    return {"role": "user", "content": (
        "The validator REJECTED your previous proposal after simulating it on the digital twin.\n"
        f"Previous proposal: {previous}\nViolations:\n{_dump(violations)}\n"
        "Revise the proposal to remove every violation. Reply with the JSON object only.")}
