import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from emirapl.agents.pipeline import BasePaperAgent  # noqa: E402
from emirapl.contracts import FaultReport, Mode, RecoveryAction, ZoneGains  # noqa: E402
from emirapl.control.pid import MultiZoneController, PIDGains  # noqa: E402
from emirapl.env.closed_loop import ClosedLoop  # noqa: E402
from emirapl.env.episode import Episode  # noqa: E402
from emirapl.env.faults import FaultSpec, apply_fault  # noqa: E402
from emirapl.env.thermal import ThermalParams, ThermalPlant  # noqa: E402
from emirapl.eval.suite import make_suite  # noqa: E402
from emirapl.llm.client import ScriptedLLM, extract_json  # noqa: E402
from emirapl.tools.twin import DigitalTwin  # noqa: E402
from emirapl.tools.validator import Validator  # noqa: E402


def warm_loop(n=2, sps=(50.0, 45.0), steps=1200):
    loop = ClosedLoop(ThermalPlant(ThermalParams(n_zones=n)), MultiZoneController(n, sps, PIDGains()))
    for _ in range(steps):
        loop.step()
    return loop


def test_tclab_steady_state_matches_hardware_range():
    p = ThermalPlant(ThermalParams(n_zones=2))
    TH = p.steady_state(np.array([100.0, 100.0]))
    assert 65 < TH[0] < 78 and 55 < TH[1] < 70  # TCLab heaters settle ~70 / ~60 degC at full power


def test_closed_loop_tracks_setpoints():
    loop = warm_loop()
    assert np.allclose(loop.plant.state.TH, [50.0, 45.0], atol=0.3)


def test_heater_degradation_makes_setpoint_unreachable():
    loop = warm_loop()
    apply_fault(loop.plant.fault, FaultSpec("heater_degradation", 0, 0.35, 0))
    for _ in range(2000):
        loop.step()
    assert loop.plant.state.TH[0] < 45.0 and loop.u[0] == pytest.approx(100.0)


def test_sensor_bias_overheats_true_temperature():
    loop = warm_loop()
    apply_fault(loop.plant.fault, FaultSpec("sensor_bias", 0, -10.0, 0))
    for _ in range(2000):
        loop.step()
    assert loop.plant.state.TH[0] > 58.0  # controller regulates the biased reading


def test_matched_twin_reproduces_plant():
    loop = warm_loop()
    report = FaultReport(detected=True, fault_class="actuator", fault_kind="heater_degradation", zone=0)
    twin = DigitalTwin("matched", ThermalParams(n_zones=2)).build(loop, report)
    ro = DigitalTwin.rollout(twin, None, 100)
    for _ in range(100):
        loop.step()
    assert np.allclose(ro.TH[-1], loop.plant.state.TH, atol=1e-6)


def test_validator_rejects_inadmissible_mode_and_ranges():
    loop = warm_loop()
    v = Validator(DigitalTwin("matched", ThermalParams(n_zones=2)), [50.0, 45.0])
    report = FaultReport(detected=True, fault_class="sensor", fault_kind="sensor_bias", zone=0)
    bad = RecoveryAction(mode=Mode.RETUNE, gains={0: ZoneGains(Kc=99, tauI=5)})
    res = v.validate(bad, loop, report)
    checks = {x.check for x in res.violations}
    assert not res.passed and "mode_admissible" in checks and res.responsible == "planner"


def test_validator_flags_unsafe_setpoint():
    loop = warm_loop()
    v = Validator(DigitalTwin("matched", ThermalParams(n_zones=2)), [50.0, 45.0])
    report = FaultReport(detected=True, fault_class="process", fault_kind="heat_loss_increase", zone=0)
    res = v.validate(RecoveryAction(mode=Mode.NORMAL, setpoints={0: 58.0}), loop, report)
    assert res.passed  # 58 degC is below the 60 degC limit and reachable
    apply_fault(loop.plant.fault, FaultSpec("sensor_bias", 0, -8.0, 0))
    res = v.validate(RecoveryAction(mode=Mode.NORMAL, setpoints={0: 58.0}), loop, report)
    assert not res.passed and any(x.check == "safety_envelope" for x in res.violations)


def test_extract_json_tolerates_fences():
    assert extract_json('Sure:\n```json\n{"a": {"b": 1}}\n```') == {"a": {"b": 1}}
    assert extract_json('prefix {"target_mode": "DERATE"} suffix')["target_mode"] == "DERATE"


def test_end_to_end_episode_with_scripted_agent():
    sc = [s for s in make_suite("t", mismatch_levels=(0.0,), seeds=(0,), zones=(2,)) if "heat_loss" in s.scenario_id][0]
    nominal = ThermalParams(n_zones=2)
    agent = BasePaperAgent(ScriptedLLM(), Validator(DigitalTwin("matched", nominal), sc.setpoints))
    res = Episode(sc).run(agent, keep_traj=False)
    m = res.metrics
    assert m["detected"] and m["action_applied"] and m["plant_success"]
    assert res.trace["applied_action"]["mode"] == "DERATE"


def test_shutdown_oracle_ignores_applied_interlock():
    sc = [s for s in make_suite("t", mismatch_levels=(0.0,), seeds=(0, 1, 2), zones=(2,))
          if "stuck_high" in s.scenario_id and s.fault["zone"] == 0 and s.fault["magnitude"] >= 90][0]
    ep = Episode(sc)
    apply_fault(ep.loop.plant.fault, ep.spec)
    required_before = ep.shutdown_required()
    ep.loop.plant.master_power = False  # a method opened the master relay
    assert required_before and ep.shutdown_required() == required_before


def test_shutdown_rejected_when_isolating_other_zones_is_safe():
    loop = warm_loop()
    apply_fault(loop.plant.fault, FaultSpec("actuator_stuck_high", 1, 85.0, 0))  # weaker (even) heater stuck
    report = FaultReport(detected=True, fault_class="actuator", fault_kind="actuator_stuck_high", zone=1)
    v = Validator(DigitalTwin("matched", ThermalParams(n_zones=2)), [50.0, 45.0])
    res = v.validate(RecoveryAction(mode=Mode.SAFE_SHUTDOWN, shutdown=True), loop, report, {1})
    assert not res.passed and any(x.check == "shutdown_justified" for x in res.violations)
