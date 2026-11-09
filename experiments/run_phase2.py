"""Run Phase 2 experiments with verified settings and per-episode checkpoints."""
import argparse
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import asdict
import hashlib
from importlib.metadata import version
from math import isfinite
import os
from pathlib import Path
import platform
import re
import time

from dotenv import load_dotenv
import pandas as pd

from emirapl.env.episode import Episode
from emirapl.env.simulation import ACCELERATED
from emirapl.eval.checkpoints import (BOOLEAN_METRICS, NUMBER_METRICS, SCHEMA_VERSION, RunDataError,
                                      load_checkpoints, read_json, record_checksum, run_lock, sha256, write_json)
from emirapl.eval.runner import build_method
from emirapl.eval.suite import load_suite
from emirapl.llm.client import PROVIDERS, ProviderError, extract_json, make_llm

ROOT = Path(__file__).resolve().parents[1]
BASE = ["base_agent_matched", "base_agent_nominal", "base_agent_no_oracle"]
FULL = ["phase2_agent"]
ABLATIONS = ["phase2_agent_no_g1", "phase2_agent_no_g2", "phase2_agent_no_g3"]
EXPERIMENTS = {
    "E1": ["no_recovery", "rule_table", "de_retune", "single_llm"],
    "E2": BASE, "E3": FULL, "E4": BASE + FULL + ABLATIONS,
    "E5": FULL + ABLATIONS, "E6": BASE + FULL + ABLATIONS,
}
PLANT_DELAY_S = 30
REPROMPT_BUDGET = 5


def execute(task):
    scenario, method, repeat, llm, path = task
    started = time.perf_counter()
    result = Episode(scenario, latency_s=PLANT_DELAY_S).run(
        build_method(method, scenario, llm, reprompt_budget=REPROMPT_BUDGET, latency_s=PLANT_DELAY_S),
        keep_traj=False,
    )
    result.metrics["episode_wall_s"] = round(time.perf_counter() - started, 3)
    record = {"scenario": asdict(scenario), "method": method, "repeat": repeat,
              "metrics": result.metrics, "trace": result.trace}
    record["checksum"] = record_checksum(record)
    write_json(path, record)
    return path


def scheduled(tasks, workers):
    if workers == 1:
        for task in tasks:
            yield execute(task)
        return
    pending = iter(tasks)
    with ProcessPoolExecutor(workers) as pool:
        active = {pool.submit(execute, task) for task in (next(pending, None) for _ in range(workers))
                  if task is not None}
        try:
            while active:
                done, active = wait(active, return_when=FIRST_COMPLETED)
                for future in done:
                    yield future.result()
                    task = next(pending, None)
                    if task is not None:
                        active.add(pool.submit(execute, task))
        finally:
            for future in active:
                future.cancel()


def failure_category(metrics):
    if metrics["plant_success"]:
        return "success"
    if metrics["safety_violation_post"]:
        return "safety"
    if metrics["false_alarm"]:
        return "false_alarm"
    if not metrics["detected"]:
        return "missed_detection"
    if not metrics["action_applied"]:
        return "no_action"
    if metrics["shutdown"] != metrics["shutdown_required"]:
        return "wrong_shutdown"
    return "tracking"


def summarize(records, out, manifest, expected):
    rows = []
    examples = {"success": [], "failure": []}
    versions = set()
    for rec in records:
        scenario, metrics = rec["scenario"], rec["metrics"]
        category = failure_category(metrics)
        if rec["method"] == "phase2_agent":
            group = examples["success" if category == "success" else "failure"]
            if len(group) < 2 and all(row["scenario"]["scenario_id"] != scenario["scenario_id"] for row in group):
                group.append(rec)
        versions.update((call["returned_model"], call.get("system_fingerprint"))
                        for call in rec["trace"].get("llm_calls", []) if call.get("returned_model"))
        rows.append({"scenario_id": scenario["scenario_id"], "fault": scenario["fault"]["kind"],
                     "mismatch": scenario["mismatch"], "noise_std": scenario["noise_std"],
                     "n_zones": scenario["n_zones"], "seed": scenario["seed"],
                     "repeat": rec["repeat"], "method": rec["method"], "failure_category": category,
                     **{key: value for key, value in metrics.items() if not isinstance(value, list)}})
    if len(rows) != expected:
        raise RunDataError("Checkpoint verification failed. Rerun the command to regenerate missing episodes.")
    frame = pd.DataFrame(rows)
    metrics = list(BOOLEAN_METRICS + NUMBER_METRICS)
    if manifest["input_price"] is not None:
        frame["estimated_cost_usd"] = (
            frame.tokens_in * manifest["input_price"] + frame.tokens_out * manifest["output_price"]
        ) / 1e6
        metrics.append("estimated_cost_usd")
    frame.to_csv(out / "summary.csv", index=False)
    write_json(out / "representative_traces.json", examples)
    frame.groupby(["method", "failure_category"]).size().rename("episodes").to_csv(out / "failure_counts.csv")
    safety = frame.groupby(["method", "repeat"])
    safety.agg(
        episodes=("scenario_id", "size"),
        plant_success_post_actuation=("plant_success", "sum"),
        plant_success_since_fault=("plant_success_since_fault", "sum"),
        safety_violations_post_actuation=("safety_violation_post", "sum"),
        safety_violations_since_fault=("safety_violation_since_fault", "sum"),
    ).to_csv(out / "safety_outcomes.csv")
    for suffix, keys in [("overall", []), ("mismatch_noise", ["mismatch", "noise_std"]), ("fault", ["fault"])]:
        grouping = ["method", *keys, "repeat"]
        per_repeat = frame.groupby(grouping)[metrics].mean()
        relevant = frame[frame.reprompts > 0].groupby(grouping).agent_success.mean().rename("reprompt_recovery")
        per_repeat = per_repeat.join(relevant)
        per_repeat.to_csv(out / f"per_repeat_{suffix}.csv")
        per_repeat.groupby(["method", *keys]).agg(["mean", "std"]).to_csv(out / f"aggregate_{suffix}.csv")
    write_json(out / "provider_observations.json", {
        "returned_versions": [{"model": model, "system_fingerprint": fingerprint}
                              for model, fingerprint in sorted(versions, key=str)],
        "missing_usage_calls": int(frame.missing_usage_calls.sum()),
        "provider_attempts": int(frame.provider_attempts.sum()),
        "representative_success_cases": len(examples["success"]),
        "representative_failure_cases": len(examples["failure"]),
    })


def validate_suite(scenarios):
    ids = [scenario.scenario_id for scenario in scenarios]
    if (not ids or any(not isinstance(sid, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,119}", sid)
                       for sid in ids)
            or len(set(sid.casefold() for sid in ids)) != len(ids)):
        raise RunDataError("Suite needs unique, filename-safe scenario IDs.")
    for scenario in scenarios:
        try:
            scenario.validate()
        except (ValueError, TypeError) as exc:
            raise RunDataError(f"Invalid scenario {scenario.scenario_id}: {exc}") from exc


def code_sha256():
    files = sorted((ROOT / "src" / "emirapl").rglob("*.py")) + [Path(__file__).resolve()]
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def run_manifest(args, suite_path, scenarios, methods, llm):
    repeats = 1 if args.provider == "scripted" else 3
    deps = ["numpy", "scipy", "pandas", "pydantic"]
    if args.provider != "scripted":
        deps.append("openai")
    if ACCELERATED:
        deps.append("numba")
    return {
        "schema_version": SCHEMA_VERSION, "experiment": args.experiment, "methods": methods, "split": args.split,
        "suite_sha256": sha256(suite_path), "scenario_ids": [scenario.scenario_id for scenario in scenarios],
        "code_sha256": code_sha256(), "provider": args.provider, "model": llm.name,
        "temperature": args.temperature if args.provider != "scripted" else None, "repeats": repeats,
        "provider_seed": None, "input_price": args.input_price, "output_price": args.output_price,
        "plant_delay_s": PLANT_DELAY_S, "reprompt_budget": REPROMPT_BUDGET,
        "llm_request": {"token_cap": llm.max_tokens, "parameters": llm.extra_body,
                        "timeout_seconds": 90, "max_attempts": llm.max_retries}
        if args.provider != "scripted" else None,
        "runtime": {"python": platform.python_version(), "os": platform.system(), "arch": platform.machine(),
                    "workers": args.workers, "numba": ACCELERATED, "dependencies": {dep: version(dep) for dep in deps},
                    "blas_threads": {key: os.environ.get(key) for key in
                                     ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS")}},
    }


def run_evaluation(args, scenarios, methods, llm, manifest):
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    with run_lock(out):
        cache = out / "episodes"
        manifest_path = out / "manifest.json"
        if manifest_path.exists():
            existing = read_json(manifest_path)
            if existing != manifest:
                raise RunDataError("Run settings or code differ from this folder's manifest. Use a fresh --out.")
        elif any(out.glob("episodes/*.json")) or (out / "summary.csv").exists():
            raise RunDataError("Existing results lack a manifest. Use a fresh --out.")
        else:
            write_json(manifest_path, manifest)
        cache.mkdir(exist_ok=True)
        tasks = [(scenario, method, repeat, llm, cache / f"{scenario.scenario_id}__{method}__{repeat}.json")
                 for repeat in range(manifest["repeats"]) for scenario in scenarios for method in methods]
        expected = len(tasks)
        assigned = {task[-1] for task in tasks}
        if any(path not in assigned for path in cache.glob("*.json")):
            raise RunDataError("The episode folder contains checkpoints outside this run's assignment.")
        completed = sum(1 for _ in load_checkpoints(tasks, out))
        pending = [task for task in tasks if not task[-1].exists()]

        def status(state, completed, **details):
            write_json(out / "completion.json", {"status": state, "completed": completed,
                                                  "expected": expected, **details})

        status("running", completed)
        (out / "gap_analysis.json").unlink(missing_ok=True)
        print(f"{completed}/{expected} saved in {out}. Starting {len(pending)} episodes.", flush=True)
        try:
            for path in scheduled(pending, args.workers):
                completed += 1
                status("running", completed, last_episode=path.name)
                print(f"[{completed}/{expected}] {path.stem}", flush=True)
            summarize(load_checkpoints(tasks, out), out, manifest, expected)
        except (ProviderError, KeyboardInterrupt) as exc:
            completed = sum(1 for _ in load_checkpoints(tasks, out))
            reason = str(exc) if isinstance(exc, ProviderError) else "Interrupted by operator."
            status("paused", completed, reason=reason)
            print(f"Paused with {completed}/{expected} saved. {reason}", flush=True)
            print("Rerun the same command to resume.", flush=True)
            return 130 if isinstance(exc, KeyboardInterrupt) else 2
        except Exception:
            completed = sum(task[-1].exists() for task in tasks)
            status("failed", completed, reason="Run or result verification failed. See the terminal error.")
            raise
        status("complete", expected, summary_sha256=sha256(out / "summary.csv"),
               manifest_sha256=sha256(manifest_path))
        print(f"Completed and verified {expected}/{expected} episodes in {out}.", flush=True)
        return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--experiment", choices=[*EXPERIMENTS, "all"], default="all")
    parser.add_argument("--split", choices=["dev", "test", "screen", "stress", "llm"], default="test")
    parser.add_argument("--provider", choices=["scripted", *PROVIDERS], default="scripted")
    parser.add_argument("--model")
    parser.add_argument("--temperature", type=float, default=.2)
    parser.add_argument("--input-price", type=float, help="USD per million input tokens")
    parser.add_argument("--output-price", type=float, help="USD per million output tokens")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--preflight", action="store_true", help="Check a live model with one short JSON request")
    args = parser.parse_args(argv)
    if args.workers < 1 or (args.provider != "scripted" and args.workers != 1):
        parser.error("Use at least one worker and only one with a live model.")
    if not isfinite(args.temperature) or not 0 <= args.temperature <= 2:
        parser.error("Temperature must be between 0 and 2.")
    if (args.input_price is None) != (args.output_price is None):
        parser.error("Supply both token prices or omit both.")
    if args.input_price is not None and (args.provider == "scripted" or
            any(not isfinite(price) or price < 0 for price in (args.input_price, args.output_price))):
        parser.error("Token prices must be finite and nonnegative and require a live provider.")
    if args.preflight and args.provider == "scripted":
        parser.error("--preflight requires a live provider.")
    if not args.preflight and args.out is None:
        parser.error("--out is required for an evaluation.")
    try:
        load_dotenv(ROOT / ".env")
        llm = make_llm(args.provider, args.model, temperature=args.temperature)
        if args.preflight:
            reply = llm.complete("preflight", [{"role": "user", "content": 'Return only the JSON object {"ok":true}.'}])
            if not reply.record.ok or extract_json(reply.text).get("ok") is not True:
                raise ProviderError("The model did not return the expected JSON. Check the provider and retry preflight.")
            model = reply.record.returned_model or llm.name
            print(f"Preflight passed for {model}.")
            return 0
        suite_path = ROOT / "configs" / "suites" / f"phase2_{args.split}.json"
        scenarios = load_suite(suite_path)
        validate_suite(scenarios)
        methods = sorted({method for group in EXPERIMENTS.values() for method in group}) if args.experiment == "all" else EXPERIMENTS[args.experiment]
        manifest = run_manifest(args, suite_path, scenarios, methods, llm)
        return run_evaluation(args, scenarios, methods, llm, manifest)
    except (ValueError, OSError, ProviderError) as exc:
        print(f"Evaluation stopped. {exc}", flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
