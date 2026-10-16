"""Print the auditable decision trace of one episode (plan -> action -> twin validation -> reprompts).

Examples
--------
python scripts/show_trace.py --run phase1_scripted_pipeline --list
python scripts/show_trace.py --run phase1_scripted_pipeline --scenario p1-z2-sensor_bias-mm20-s1 --method base_agent_nominal
"""
from __future__ import annotations

import argparse
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(run: str):
    path = ROOT / "results" / run / "episodes.jsonl"
    if not path.exists():
        raise SystemExit(f"{path} not found (episodes.jsonl is local-only; re-run scripts/run_eval.py to create it)")
    with path.open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def fmt_action(a: dict | None) -> str:
    if not a:
        return "(none)"
    parts = [a["mode"]]
    for key in ("setpoints", "q_max", "sensor_offset"):
        if a.get(key):
            parts.append(f"{key}={a[key]}")
    if a.get("gains"):
        parts.append("gains=" + ", ".join(f"z{z}:Kc={g['Kc']},tauI={g['tauI']}" for z, g in a["gains"].items()))
    if a.get("shutdown"):
        parts.append("SHUTDOWN")
    return " | ".join(parts)


def show(ep: dict) -> None:
    sc, tr, m = ep["scenario"], ep["trace"], ep["metrics"]
    f = sc["fault"]
    print(f"\n=== {sc['scenario_id']}  [{ep['method']}]")
    print(f"true fault : {f['kind']} zone {f['zone']} magnitude {f['magnitude']} at t={f['onset_s']:.0f}s "
          f"(mismatch {sc['mismatch']:.0%})")
    if not tr:
        print("no decision (fault not detected)")
        return
    rep = tr.get("fault_report") or {}
    print(f"detected   : t={rep.get('t_detect_s')}s symptoms={rep.get('symptoms')}")
    print(f"localised  : {rep.get('fault_kind')} zone {rep.get('zone')} ({rep.get('localisation_source')})")
    for i, p in enumerate(tr.get("plans", [])):
        print(f"plan {i}     : {p['target_mode']}  - {p.get('rationale', '')[:110]}")
    for i, (a, v) in enumerate(zip(tr.get("actions", []), tr.get("validations", []))):
        verdict = "PASS" if v["passed"] else f"FAIL -> {v['responsible']}"
        print(f"action {i}   : {fmt_action(a)}")
        print(f"  validate : {verdict}  predicted={v.get('predicted')}")
        for viol in v.get("violations", []):
            print(f"    - [{viol['check']}] {viol['message']}")
    print(f"applied    : {fmt_action(tr.get('applied_action'))}  fallback={tr.get('used_fallback')}  "
          f"reprompts={tr.get('reprompts')}")
    calls = tr.get("llm_calls", [])
    if calls:
        print(f"llm calls  : {len(calls)}  tokens in/out={sum(c['tokens_in'] for c in calls)}/"
              f"{sum(c['tokens_out'] for c in calls)}  latency={sum(c['latency_s'] for c in calls):.1f}s  model={calls[0]['model']}")
    print(f"TRUE PLANT : success={m['plant_success']}  safety_violation={m['safety_violation_post']}  "
          f"max_T={m['max_T_post']}  regulated={m['regulated']}  validated_but_failed={m['validated_but_failed']}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--scenario")
    ap.add_argument("--method")
    ap.add_argument("--list", action="store_true", help="list episodes that were validated but failed on the plant")
    args = ap.parse_args()
    eps = load(args.run)
    if args.list:
        for ep in eps:
            m = ep["metrics"]
            flag = "VALIDATED-BUT-FAILED" if m.get("validated_but_failed") else ("ok" if m["plant_success"] else "failed")
            print(f"{ep['scenario']['scenario_id']:45s} {ep['method']:22s} {flag}")
        return
    sel = [e for e in eps if (not args.scenario or e["scenario"]["scenario_id"] == args.scenario)
           and (not args.method or e["method"] == args.method)]
    if not sel:
        raise SystemExit("no matching episode (use --list)")
    for ep in sel:
        show(ep)


if __name__ == "__main__":
    main()
