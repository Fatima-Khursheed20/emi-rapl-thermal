"""Run methods over an evaluation suite and aggregate results."""
from __future__ import annotations

import json
import time
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from ..agents.pipeline import BasePaperAgent
from ..baselines.methods import DERetune, NoRecovery, RuleTable, SingleCallLLM
from ..env.episode import Episode, Scenario
from ..env.thermal import ThermalParams
from ..tools.twin import DigitalTwin
from ..tools.validator import Validator

METHODS = ["no_recovery", "rule_table", "single_llm", "de_retune", "base_agent_matched", "base_agent_nominal"]


def build_method(name: str, sc: Scenario, llm=None, reprompt_budget: int = 5, latency_s: float | None = 30.0):
    nominal = ThermalParams(n_zones=sc.n_zones)
    delay = 30.0 if latency_s is None else latency_s
    if name == "no_recovery":
        return NoRecovery()
    if name == "rule_table":
        return RuleTable()
    if name == "single_llm":
        return SingleCallLLM(llm)
    if name.startswith("de_retune"):
        mode = "matched" if name.endswith("matched") else "nominal"
        return DERetune(Validator(DigitalTwin(mode, nominal), sc.setpoints, delay_s=delay))
    if name.startswith("base_agent"):
        mode = name.split("_")[-1]
        return BasePaperAgent(llm, Validator(DigitalTwin(mode, nominal), sc.setpoints, delay_s=delay), reprompt_budget,
                              name=f"base_agent_{mode}")
    raise ValueError(name)


def run(scenarios: list[Scenario], methods: list[str], llm, out_dir: str | Path, latency_s: float | None = 30.0,
        keep_traj: bool = False, verbose: bool = True) -> pd.DataFrame:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ep_file = (out / "episodes.jsonl").open("a", encoding="utf-8")
    done = set()
    if (out / "summary.csv").exists():
        prev = pd.read_csv(out / "summary.csv")
        done = set(zip(prev.scenario_id, prev.method))
    rows = []
    for sc in scenarios:
        for m in methods:
            if (sc.scenario_id, m) in done:
                continue
            t0 = time.time()
            res = Episode(sc, latency_s=latency_s).run(build_method(m, sc, llm, latency_s=latency_s), keep_traj=keep_traj)
            row = {"scenario_id": sc.scenario_id, "method": m, "llm": getattr(llm, "name", None) if "llm" in m or "agent" in m else None,
                   "n_zones": sc.n_zones, "fault": sc.fault["kind"], "fault_zone": sc.fault["zone"],
                   "magnitude": sc.fault["magnitude"], "mismatch": sc.mismatch, "seed": sc.seed,
                   **{k: v for k, v in res.metrics.items() if not isinstance(v, list)}, "run_s": round(time.time() - t0, 2)}
            rows.append(row)
            ep_file.write(json.dumps({"scenario": asdict(sc), "method": m, "metrics": res.metrics, "trace": res.trace,
                                      "traj": res.traj}) + "\n")
            ep_file.flush()
            pd.DataFrame([row]).to_csv(out / "summary.csv", mode="a", header=not (out / "summary.csv").exists(), index=False)
            if verbose:
                print(f"{sc.scenario_id:45s} {m:20s} agent_ok={row['agent_success']!s:5s} plant_ok={row['plant_success']!s:5s} "
                      f"maxT={row['max_T_post']:6.2f} reprompts={row['reprompts']} fb={row['used_fallback']!s:5s} ({row['run_s']}s)",
                      flush=True)
    ep_file.close()
    return pd.read_csv(out / "summary.csv")


def aggregate(df: pd.DataFrame, by=("method",)) -> pd.DataFrame:
    g = df.groupby(list(by))
    return pd.DataFrame({
        "episodes": g.size(),
        "agent_success_%": (g.agent_success.mean() * 100).round(1),
        "plant_success_%": (g.plant_success.mean() * 100).round(1),
        "validated_but_failed_%": (g.validated_but_failed.mean() * 100).round(1),
        "safety_violation_%": (g.safety_violation_post.mean() * 100).round(1),
        "fallback_%": (g.used_fallback.mean() * 100).round(1),
        "mean_reprompts": g.reprompts.mean().round(2),
        "setpoint_retention": g.setpoint_retention.mean().round(3),
        "mean_llm_calls": g.llm_calls.mean().round(2),
        "mean_tokens_in": g.tokens_in.mean().round(0),
        "mean_llm_latency_s": g.llm_latency_s.mean().round(2),
    })
