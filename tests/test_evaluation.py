"""Regression tests for final evaluation, provider failures and simulator boundaries."""
from dataclasses import replace
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import openai
from openai import _base_client
import pytest

from emirapl.agents.pipeline import BasePaperAgent
from emirapl.contracts import DecisionTrace, FaultReport, LLMCallRecord, RecoveryAction, ValidationResult
from emirapl.env.episode import Episode
from emirapl.env.faults import FaultSpec, apply_fault
from emirapl.eval.checkpoints import RunDataError, read_json, run_lock, sha256
from emirapl.eval.runner import build_method
from emirapl.eval.suite import load_suite
from emirapl.llm.client import LLMClient, LLMResponse, ProviderError, QuotaExhausted, extract_json, make_llm
from emirapl.tools.twin import DigitalTwin, Rollout
from experiments import analyze_phase2, run_phase2

SUITES = Path(__file__).resolve().parents[1] / "configs" / "suites"
SCENARIO = load_suite(SUITES / "phase2_dev.json")[0]
MODEL = "openai/gpt-oss-20b"
MESSAGES = [{"role": "user", "content": 'Return the JSON object {"ok": true}'}]


def sdk_reply(model=MODEL, text='{"ok":true}', finish="stop"):
    return {
        "id": "test-response", "object": "chat.completion", "created": 0, "model": model,
        "system_fingerprint": "test-fingerprint",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 25, "completion_tokens": 12, "total_tokens": 37},
    }


@pytest.fixture
def sdk_mock(monkeypatch):
    """Send real SDK requests through an in-memory HTTP transport."""
    http = getattr(_base_client, "httpx2", None) or _base_client.httpx
    openai_client = openai.OpenAI
    clients = []
    monkeypatch.setenv("GROQ_API_KEY", "unit-test-token")

    def install(handler):
        def create(*args, **kwargs):
            transport = http.MockTransport(handler)
            kwargs["http_client"] = http.Client(transport=transport)
            client = openai_client(*args, **kwargs)
            clients.append(client)
            return client
        monkeypatch.setattr(openai, "OpenAI", create)
        return http

    yield install
    for client in clients:
        client.close()


def test_groq_retries_429_honors_retry_after_and_accounts_usage(sdk_mock, monkeypatch):
    payloads, pauses = [], []

    def respond(request):
        payloads.append(json.loads(request.content))
        if len(payloads) == 1:
            return http.Response(429, json={"error": {"message": "tokens per minute"}}, headers={"retry-after": "0.25"})
        return http.Response(200, json=sdk_reply())

    http = sdk_mock(respond)
    monkeypatch.setattr("emirapl.llm.client.time.sleep", pauses.append)
    response = LLMClient("groq", min_interval_s=0).complete("planner", MESSAGES)
    assert pauses == [.25]
    assert len(payloads) == response.record.api_attempts == 2
    assert payloads[0]["reasoning_effort"] == "low"
    assert payloads[0]["max_completion_tokens"] == 2048
    assert "max_tokens" not in payloads[0]
    assert response.record.usage_reported and response.record.tokens_in == 25
    assert response.record.system_fingerprint == "test-fingerprint"


@pytest.mark.parametrize(("status", "code", "message", "error"), [
    (401, "invalid_api_key", "credential unit-test-token", ProviderError),
    (403, "permission_denied", "model forbidden", ProviderError),
    (404, "model_not_found", "model missing", ProviderError),
    (400, "invalid_request_error", "unsupported parameter", ProviderError),
    (429, "rate_limit_exceeded", "tokens per day (TPD)", QuotaExhausted),
    (429, "insufficient_quota", "quota depleted", QuotaExhausted),
])
def test_permanent_provider_failure_is_not_an_agent_result(sdk_mock, status, code, message, error):
    calls = []

    def respond(request):
        calls.append(request)
        return http.Response(status, json={"error": {"code": code, "message": message}})

    http = sdk_mock(respond)
    with pytest.raises(error) as info:
        LLMClient("groq").complete("action", MESSAGES)
    assert len(calls) == 1
    assert "unit-test-token" not in str(info.value)


@pytest.mark.parametrize("failure", ["overloaded", "connection"])
def test_transient_exhaustion_pauses_after_bounded_attempts(sdk_mock, monkeypatch, failure):
    calls, sleeps = [], []

    def respond(request):
        calls.append(request)
        if failure == "connection":
            raise http.ConnectError("test disconnected", request=request)
        return http.Response(503, json={"error": {"message": "overloaded"}})

    http = sdk_mock(respond)
    monkeypatch.setattr("emirapl.llm.client.time.sleep", sleeps.append)
    with pytest.raises(ProviderError, match="after 3 attempt"):
        LLMClient("groq", max_retries=3, min_interval_s=0).complete("planner", MESSAGES)
    assert len(calls) == 3 and sleeps == [2., 4.]


def test_provider_json_rejection_can_recover_with_plain_request(sdk_mock):
    payloads = []

    def respond(request):
        payloads.append(json.loads(request.content))
        if len(payloads) == 1:
            return http.Response(400, json={"error": {"code": "json_validate_failed", "message": "failed JSON"}})
        return http.Response(200, json=sdk_reply())

    http = sdk_mock(respond)
    result = LLMClient("groq", min_interval_s=0).complete("action", MESSAGES)
    assert result.record.ok and result.record.api_attempts == 2
    assert payloads[0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in payloads[1]


def test_truncated_model_response_is_visible_and_rejected(sdk_mock):
    def respond(request):
        return http.Response(200, json=sdk_reply(finish="length"))

    http = sdk_mock(respond)
    result = LLMClient("groq").complete("action", MESSAGES)
    assert not result.record.ok and result.record.finish_reason == "length"
    assert result.record.tokens_out == 12


@pytest.mark.parametrize("model", ["openai/gpt-oss-20b", "openai/gpt-oss-120b"])
def test_cli_preflight_for_both_approved_models(sdk_mock, model):
    def respond(request):
        assert json.loads(request.content)["model"] == model
        return http.Response(200, json=sdk_reply(model=model))

    http = sdk_mock(respond)
    assert run_phase2.main(["--provider", "groq", "--model", model, "--preflight"]) == 0


@pytest.mark.parametrize("text", ['{"outer":{"mode":"NORMAL"}', '[{"mode":"NORMAL"}]',
                                  '{"mode":"DERATE","mode":"NORMAL"}', '{"q":NaN}',
                                  '{"mode":"NORMAL"} {"mode":"DERATE"}'])
def test_parser_rejects_ambiguous_or_incomplete_proposals(text):
    with pytest.raises(ValueError):
        extract_json(text)


def test_checkpoints_pause_resume_reject_mixing_and_recover_corruption(tmp_path, monkeypatch):
    out = tmp_path / "run"
    scenarios = load_suite(SUITES / "phase2_dev.json")[:2]
    monkeypatch.setattr(run_phase2, "load_suite", lambda path: scenarios)
    execute = run_phase2.execute
    attempts = []

    def pause_after_one(task):
        attempts.append(task[-1])
        if len(attempts) > 1:
            raise QuotaExhausted("test quota")
        return execute(task)

    monkeypatch.setattr(run_phase2, "execute", pause_after_one)
    argv = ["--experiment", "E3", "--split", "dev", "--out", str(out)]
    assert run_phase2.main(argv) == 2
    assert read_json(out / "completion.json")["completed"] == 1
    assert not (out / "summary.csv").exists()
    assert analyze_phase2.main([str(out)]) == 2
    old_hash = sha256(attempts[0])

    monkeypatch.setattr(run_phase2, "execute", execute)
    assert run_phase2.main(argv) == 0
    assert sha256(attempts[0]) == old_hash
    assert analyze_phase2.main([str(out)]) == 0
    assert read_json(out / "completion.json")["status"] == "complete"
    assert run_phase2.main(argv + ["--workers", "2"]) == 2

    record = read_json(attempts[1])
    record["metrics"]["plant_success"] = not record["metrics"]["plant_success"]
    attempts[1].write_text(json.dumps(record), encoding="utf-8")
    assert analyze_phase2.main([str(out)]) == 2
    assert run_phase2.main(argv) == 0
    assert len(list((out / "rejected_checkpoints").glob("*.json"))) == 1
    assert sha256(attempts[0]) == old_hash
    assert analyze_phase2.main([str(out)]) == 0

    with (out / "summary.csv").open("a", encoding="utf-8") as file:
        file.write("invalid edit\n")
    assert analyze_phase2.main([str(out)]) == 2


def test_result_folder_cannot_be_written_concurrently(tmp_path):
    with run_lock(tmp_path), pytest.raises(RunDataError, match="in use"):
        with run_lock(tmp_path):
            pytest.fail("concurrent writer entered")
    with run_lock(tmp_path):
        pass


def test_locked_splits_and_replication_grid():
    scenarios = {split: load_suite(SUITES / f"phase2_{split}.json") for split in
                 ("dev", "test", "screen", "stress", "llm")}
    for suite in scenarios.values():
        run_phase2.validate_suite(suite)
    assert len(scenarios["test"]) == 400
    assert len(scenarios["llm"]) * len(set(sum(run_phase2.EXPERIMENTS.values(), []))) * 3 == 660
    assert {s.scenario_id for s in scenarios["llm"]} <= {s.scenario_id for s in scenarios["test"]}
    for split in ("dev", "screen", "stress"):
        assert not ({s.seed for s in scenarios[split]} & {s.seed for s in scenarios["test"]})


def test_single_call_handles_zero_integral_time_without_twin():
    ep = Episode(SCENARIO)
    reply = LLMResponse('{"mode":"RETUNE","gains":{"0":{"Kc":5,"tauI":0}}}',
                        LLMCallRecord(agent="single", model="test", latency_s=0))
    client = SimpleNamespace(complete=lambda *args: reply)
    method = build_method("single_llm", SCENARIO, client)
    snap = ep.snapshot({"t": [], "y": [], "u": []})
    trace = method.decide(snap, FaultReport(detected=True), ep.loop)
    ep.loop.apply(trace.applied_action)
    assert ep.loop.ctrl.loops[0].gains.tauI == 20.
    assert np.isfinite(ep.loop.step()).all()
    assert not trace.validated_action


def test_normal_cannot_change_controller_parameters():
    ep = Episode(SCENARIO)
    agent = build_method("phase2_agent", SCENARIO, make_llm("scripted"))
    action = RecoveryAction(mode="NORMAL", q_max={0: 30})
    result = agent.validator.validate(action, ep.loop, FaultReport(detected=True))
    assert not result.passed
    assert any(v.check == "mode_fields" for v in result.violations)


def test_safety_duration_counts_any_zone_and_separates_delay(monkeypatch):
    ep = Episode(SCENARIO)
    agent = build_method("phase2_agent", SCENARIO, make_llm("scripted"))
    temperatures = np.tile(SCENARIO.setpoints, (400, 1))
    temperatures[:30, 0] = 67.
    temperatures[30:70, 0] = 60.3
    temperatures[70:110, 1] = 60.3
    rollout = Rollout(np.arange(400), temperatures, temperatures, temperatures, np.array(SCENARIO.setpoints), 30)
    monkeypatch.setattr(DigitalTwin, "rollout", lambda *args: rollout)
    validation = agent.validator.validate(RecoveryAction(mode="NORMAL"), ep.loop, FaultReport(detected=True))
    assert not validation.passed and validation.predicted["post_action_safety"]["above_s"] == 80
    assert validation.predicted["during_delay_safety"]["peak_degC"] == 67
    start = int(ep.spec.onset_s)
    history = {"t": np.arange(start+1, start+401), "TH": temperatures,
               "sp": np.tile(SCENARIO.setpoints, (400, 1))}
    metrics = ep.evaluate(history, None, None, start+30)
    assert metrics["safety_violation_post"] and metrics["time_above_limit_post_s"] == 80


def test_operator_sees_exact_replacement_shutdown(monkeypatch):
    ep = Episode(SCENARIO)
    agent = build_method("phase2_agent_no_g1", SCENARIO, make_llm("scripted"))
    agent.diagnosis = False
    shown = []
    agent.approval = lambda action: shown.append(action) or False
    fallback = RecoveryAction(mode="DERATE", setpoints={0: 35.})
    shutdown = RecoveryAction(mode="SAFE_SHUTDOWN", shutdown=True)
    monkeypatch.setattr(BasePaperAgent, "decide", lambda *args: DecisionTrace(
        method=agent.name, used_fallback=True, applied_action=fallback))
    monkeypatch.setattr(agent.validator, "validate", lambda *args: ValidationResult(passed=False))
    monkeypatch.setattr(agent, "emergency_shutdown", lambda *args: shutdown)
    snap = ep.snapshot({"t": [], "y": [], "u": []})
    trace = agent.decide_observed(snap, FaultReport(detected=True), ep.loop, ([], []))
    assert shown == [shutdown] and trace.selected_action == shutdown
    assert trace.applied_action is None


@pytest.mark.parametrize("detect_at", [2, 5])
def test_oracle_and_actuation_respect_actual_fault_and_episode_boundaries(detect_at):
    scenario = replace(SCENARIO, t_end_s=5, fault={**SCENARIO.fault, "onset_s": 3})
    ep = Episode(scenario, latency_s=0)
    ep.monitor = SimpleNamespace(residual=np.zeros(ep.loop.n), mu=np.zeros(ep.loop.n),
                                 update=lambda t, *args: FaultReport(detected=True) if t == detect_at else None)
    method = SimpleNamespace(name="test", decide=lambda snap, report, loop: DecisionTrace(
        method="test", fault_report=report, applied_action=RecoveryAction(mode="SAFE_SHUTDOWN", shutdown=True)))
    result = ep.run(method)
    if detect_at == 2:
        assert result.metrics["false_alarm"]
        assert result.trace["fault_report"]["localisation_source"] == "none"
    else:
        assert result.trace["selected_action"]["shutdown"]
        assert result.trace["applied_action"] is None
        assert ep.loop.plant.master_power and not result.metrics["action_applied"]


def test_rollout_agrees_with_stepwise_plant_after_delayed_shutdown():
    ep = Episode(SCENARIO)
    loop = ep.loop
    apply_fault(loop.plant.fault, FaultSpec("actuator_stuck_high", 0, 95., 0.))
    apply_fault(loop.plant.fault, FaultSpec("sensor_bias", 1, -4., 0.))
    for _ in range(30):
        loop.step()
    loop.plant.noise_std = 0.
    action = RecoveryAction(mode="SAFE_SHUTDOWN", shutdown=True)
    rollout = DigitalTwin.rollout(loop, action, 30, delay_s=3.5)
    reference = loop.clone()
    for i in range(34):
        if i == 4:
            reference.apply(action)
        reading = reference.step()
        np.testing.assert_allclose(rollout.TH[i], reference.plant.state.TH, atol=1e-9)
        np.testing.assert_allclose(rollout.y[i], reading, atol=1e-9)
        np.testing.assert_allclose(rollout.u[i], reference.plant.last_Q, atol=1e-9)
    assert rollout.hold == 4 and rollout.t[-1] == 34


def test_keyboard_interrupt_records_empty_pause_without_results(tmp_path, monkeypatch):
    out = tmp_path / "run"
    monkeypatch.setattr(run_phase2, "load_suite", lambda _: [SCENARIO])

    def interrupt(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(run_phase2, "execute", interrupt)
    assert run_phase2.main(["--experiment", "E3", "--split", "dev", "--out", str(out)]) == 130
    progress = read_json(out / "completion.json")
    assert (progress["status"], progress["completed"], progress["expected"]) == ("paused", 0, 1)
    assert not (out / "summary.csv").exists()


def test_missing_key_fails_preflight_before_evaluation(sdk_mock, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY")
    monkeypatch.setattr(run_phase2, "load_dotenv", lambda path: None)
    assert run_phase2.main(["--provider", "groq", "--preflight"]) == 2


def test_global_and_local_loss_compose_independently_of_injection_order():
    first, second = Episode(SCENARIO), Episode(SCENARIO)
    a = FaultSpec("heat_loss_increase", 0, 3., 0.)
    b = FaultSpec("local_insulation_loss", 1, 2., 0.)
    for ep, sequence in ((first, (a, b)), (second, (b, a))):
        for spec in sequence:
            apply_fault(ep.loop.plant.fault, spec)
    np.testing.assert_allclose(first.loop.plant.physics()[0], second.loop.plant.physics()[0])
    np.testing.assert_allclose(first.loop.plant.physics()[0], first.loop.plant.p.U * [3, 6])


@pytest.mark.parametrize(("fault", "message"), [
    ({"onset_s": 4200.}, "onset"), ({"zone": 99}, "zone"), ({"magnitude": float("nan")}, "magnitude"),
])
def test_invalid_scenario_fails_before_stepping(fault, message):
    with pytest.raises(ValueError, match=message):
        Episode(replace(SCENARIO, fault={**SCENARIO.fault, **fault}))


def test_interactive_demo_rejects_invalid_scenario_index(tmp_path):
    from scripts import phase2_demo

    assert phase2_demo.main(["--scenario", "-1", "--out", str(tmp_path / "demo.json")]) == 2
    assert not (tmp_path / "demo.json").exists()


def test_analysis_keeps_variants_and_repeats_in_the_same_seed_block():
    import pandas as pd

    rows = []
    for seed in (20, 21):
        for fault in ("sensor_bias", "heater_degradation"):
            for repeat in range(3):
                for method, success in (("full", True), ("baseline", seed == 20)):
                    rows.append({"n_zones": 2, "seed": seed, "fault": fault, "scenario_id": f"{fault}-{seed}",
                                 "repeat": repeat, "method": method, "plant_success": success, "decision_wall_s": 1.})
    result = analyze_phase2.paired(pd.DataFrame(rows), "full", "baseline")
    assert result["pairs"] == 12 and result["scenario_blocks"] == 2
    assert result["delta"] == .5 and result["ci95"] is None


def test_g3_ablation_uses_symptoms_and_retains_calibration():
    agent = build_method("phase2_agent_no_g3", SCENARIO, make_llm("scripted"))
    result = Episode(SCENARIO).run(agent, keep_traj=False)
    report = result.trace["fault_report"]
    assert report["symptoms"]
    assert report["fault_kind"] is None and report["zone"] is None
    assert report["localisation_source"] == "none"
    assert result.metrics["gain_scale_rmse"] is not None
    tools = {event["tool"] for event in result.trace["tool_events"]}
    assert "fault_replay" not in tools and "diagnosis_selection" not in tools


def test_since_fault_success_flags_earlier_violation_and_counts_repairs():
    ep = Episode(SCENARIO)
    onset = int(ep.spec.onset_s)
    temperatures = np.tile(SCENARIO.setpoints, (10, 1))
    temperatures[0, 0] = 60.8
    history = {"t": np.arange(onset + 1, onset + 11), "TH": temperatures,
               "sp": np.tile(SCENARIO.setpoints, (10, 1))}
    trace = DecisionTrace(method="test", tool_events=[
        {"tool": "bounded_de_repair", "passed": False},
        {"tool": "bounded_de_repair", "passed": True},
    ])
    metrics = ep.evaluate(history, trace, None, onset + 2)
    assert metrics["plant_success"]
    assert not metrics["plant_success_since_fault"]
    assert not metrics["safety_violation_post"] and metrics["safety_violation_since_fault"]
    assert metrics["repair_attempts"] == 2 and metrics["repairs_validated"] == 1
