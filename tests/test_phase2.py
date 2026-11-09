import numpy as np
import pytest
from pydantic import ValidationError

from emirapl.contracts import DecisionTrace, FaultReport, RecoveryAction
from emirapl.env.episode import Episode
from emirapl.env.thermal import ThermalParams
from emirapl.eval.runner import build_method
from emirapl.eval.suite import load_suite
from emirapl.llm.client import make_llm
from emirapl.tools.calibration import replay


def test_replay_identifies_sensor_jump():
    y = np.tile([23., 23.], (21, 1))
    y[10:, 1] -= 10.
    ranked = replay(ThermalParams(), y, np.zeros_like(y))
    assert (ranked[0]["kind"], ranked[0]["zone"]) == ("sensor_bias", 1)


def test_phase2_no_oracle_and_approval_can_veto():
    scenarios = load_suite("configs/suites/phase2_dev.json")
    scenario = next(s for s in scenarios if s.fault["kind"] == "heater_degradation")
    agent = build_method("phase2_agent", scenario, make_llm("scripted"))
    agent.approval = lambda action: False
    result = Episode(scenario).run(agent, keep_traj=False)
    assert result.trace["fault_report"]["localisation_source"] == "diagnosis"
    assert any(e["tool"] == "adaptive_ekf" for e in result.trace["tool_events"])
    assert any(e["tool"] == "operator_approval" for e in result.trace["tool_events"])
    assert result.trace["applied_action"] is None
    assert not result.metrics["action_applied"]


def test_actions_reject_nonfinite_values():
    with pytest.raises(ValidationError):
        RecoveryAction(mode="DERATE", setpoints={0: float("nan")})


@pytest.mark.parametrize(("suffix", "field"), [("no_g1", "calibration"), ("no_g2", "repair"), ("no_g3", "diagnosis")])
def test_ablation_switches(suffix, field):
    scenario = load_suite("configs/suites/phase2_dev.json")[0]
    agent = build_method("phase2_agent_" + suffix, scenario, make_llm("scripted"))
    assert not getattr(agent, field)
    assert sum([agent.calibration, agent.repair, agent.diagnosis]) == 2


def test_numeric_repair_revalidates_a_rejected_sensor_offset():
    scenario = next(s for s in load_suite("configs/suites/phase2_dev.json") if s.fault["kind"] == "sensor_bias")
    loop = Episode(scenario).loop
    loop.y = np.asarray(scenario.setpoints, dtype=float)
    agent = build_method("phase2_agent_no_g1", scenario, make_llm("scripted"))
    zone = scenario.fault["zone"]
    report = FaultReport(detected=True, fault_kind="sensor_bias", fault_class="sensor", zone=zone)
    proposal = RecoveryAction(mode="SENSOR_CORRECTION", sensor_offset={zone: 0})
    rejected = agent.validator.validate(proposal, loop, report)
    trace = DecisionTrace(method=agent.name)
    repaired, verified = agent.refine(proposal, rejected, loop, report, set(), trace)
    assert not rejected.passed
    assert verified.passed
    assert repaired.sensor_offset[zone] > 0
    assert trace.tool_events[-1]["tool"] == "bounded_de_repair"


def test_repair_never_simulates_nonexistent_zone():
    scenario = load_suite("configs/suites/phase2_dev.json")[0]
    loop = Episode(scenario).loop
    agent = build_method("phase2_agent_no_g1", scenario, make_llm("scripted"))
    report = FaultReport(detected=True, fault_class="actuator", fault_kind="heater_degradation", zone=0)
    action = RecoveryAction(mode="DERATE", setpoints={0: 0, 99: 35})
    result = agent.validator.validate(action, loop, report)
    trace = DecisionTrace(method=agent.name)
    assert agent.refine(action, result, loop, report, set(), trace) == (action, result)
    assert not trace.tool_events


def test_unapplied_shutdown_is_not_counted():
    scenario = load_suite("configs/suites/phase2_dev.json")[0]
    episode = Episode(scenario)
    onset = scenario.fault["onset_s"]
    history = {"t": np.asarray([onset + 1]), "TH": np.asarray([scenario.setpoints]),
               "sp": np.asarray([scenario.setpoints])}
    trace = DecisionTrace(method="test", applied_action=RecoveryAction(mode="SAFE_SHUTDOWN", shutdown=True))
    metrics = episode.evaluate(history, trace, None, None)
    assert not metrics["action_applied"]
    assert not metrics["agent_success"]
    assert not metrics["shutdown"]


@pytest.mark.parametrize("mismatch", [0, .3])
def test_stuck_heater_emergency_power_cut(mismatch):
    scenario = next(s for s in load_suite("configs/suites/phase2_screen.json")
                    if s.n_zones == 4 and s.fault["kind"] == "actuator_stuck_high" and s.mismatch == mismatch)
    agent = build_method("phase2_agent", scenario, make_llm("scripted"))
    result = Episode(scenario).run(agent, keep_traj=False)
    assert result.metrics["shutdown"]
    assert not result.metrics["safety_violation_post"]
    assert any(e["tool"] == "plant_actuation" for e in result.trace["tool_events"])


def test_secondary_fault_respects_its_own_onset():
    from dataclasses import replace

    original = load_suite("configs/suites/phase2_dev.json")[0]
    scenario = replace(original, t_end_s=30, noise_std=0, mismatch=0,
                       fault={"kind": "heater_degradation", "zone": 0, "magnitude": .5, "onset_s": 5},
                       secondary_faults=[{"kind": "sensor_bias", "zone": 1, "magnitude": -10, "onset_s": 15}])
    result = Episode(scenario).run(build_method("no_recovery", scenario))
    control = Episode(replace(scenario, secondary_faults=[])).run(build_method("no_recovery", scenario))
    assert result.traj["y"][2][1] == control.traj["y"][2][1]
    assert control.traj["y"][3][1] - result.traj["y"][3][1] == pytest.approx(10)


def test_json_reply_handles_braces_inside_rationale():
    from emirapl.llm.client import extract_json

    assert extract_json('Result: {"rationale": "threshold } reached", "index": 0}')["index"] == 0
