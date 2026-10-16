"""Aggregate result CSVs into the two tables used by the Phase-1 document (results.json)."""
import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(sys.argv[1])
OUT = Path(__file__).with_name("results.json")
R = REPO / "results"


def load(run_glob, label_fn):
    frames = []
    for f in sorted(p for p in R.glob(run_glob) if p.is_dir() and (p / "summary.csv").exists()):
        d = pd.read_csv(f / "summary.csv")
        d["label"] = d.apply(lambda r: label_fn(r, f.name), axis=1)
        frames.append(d)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


NAMES = {"no_recovery": "B0 No recovery", "rule_table": "B1 Rule table", "de_retune": "B3 DE retune (nominal twin)",
         "single_llm": "B2 Single LLM call", "base_agent_matched": "B4 Base workflow, matched twin",
         "base_agent_nominal": "B4 Base workflow, nominal twin"}


def label(r, run):
    name = NAMES[r.method]
    if "scripted" in run:
        return name + " (scripted proposer)"
    if run.startswith("phase1_llm_"):
        return name + " [" + ("gpt-oss-120b" if "120b" in run else "gpt-oss-20b") + "]"
    return name


full = pd.concat([load("phase1_nonllm", label), load("phase1_de_*", label), load("phase1_scripted_pipeline", label)])
llm = load("phase1_llm_*", label)
subset = set(llm.scenario_id)  # compare on exactly the scenarios the LLM runs covered
sub = pd.concat([full[full.scenario_id.isin(subset) & ~full.label.str.contains("scripted")], llm])

ORDER = list(NAMES.values())


def order_key(lbl):
    for i, n in enumerate(ORDER):
        if lbl.startswith(n):
            return (i, lbl)
    return (99, lbl)


def pct(x):
    return f"{100 * x:.1f}"


def rows_full(d):
    out = []
    for lbl, g in sorted(d.groupby("label"), key=lambda kv: order_key(kv[0])):
        out.append([lbl, str(len(g)), pct(g.plant_success.mean()), pct(g.agent_success.mean()) if "B4" in lbl else "–",
                    pct(g.validated_but_failed.mean()) if "B4" in lbl else "–", pct(g.safety_violation_post.mean()),
                    pct(g.used_fallback.mean()) if "B4" in lbl else "–", f"{g.setpoint_retention.mean():.2f}"])
    return out


def rows_llm(d):
    out = []
    for lbl, g in sorted(d.groupby("label"), key=lambda kv: order_key(kv[0])):
        is_llm = "[" in lbl
        needed = g[g.reprompts > 0]
        rec = pct(needed.agent_success.mean()) if ("B4" in lbl and len(needed)) else "–"
        out.append([lbl, str(len(g)), pct(g.plant_success.mean()), pct(g.agent_success.mean()) if "B4" in lbl else "–",
                    pct(g.validated_but_failed.mean()) if "B4" in lbl else "–", pct(g.safety_violation_post.mean()),
                    f"{g.reprompts.mean():.2f}" if "B4" in lbl else "–", rec,
                    f"{g.llm_calls.mean():.1f}" if is_llm else "–", f"{(g.tokens_in + g.tokens_out).mean() / 1000:.1f}k" if is_llm else "–",
                    f"{g.decision_wall_s.mean():.0f}" if is_llm or "DE" in lbl else "–"])
    return out


res = {
    "full": {"headers": ["Method", "n", "Plant success %", "Agent success %", "Validated-but-failed %", "Safety violation %", "Fallback %", "Setpoint retention"],
             "rows": rows_full(full), "widths": [2626, 450, 950, 950, 1100, 950, 1000, 1000]},
    "llm": {"headers": ["Method", "n", "Plant %", "Agent %", "VbF %", "Unsafe %", "Reprompts", "Recovery %", "Calls", "Tokens", "Time (s)"],
            "rows": rows_llm(sub), "widths": [2426, 350, 620, 620, 620, 650, 800, 780, 560, 650, 950]},
    "by_fault": {f"{lbl}": {k: round(100 * v, 1) for k, v in g.groupby("fault").plant_success.mean().items()}
                 for lbl, g in pd.concat([full, llm]).groupby("label")},
}
OUT.write_text(json.dumps(res, indent=1))
for k in ("full", "llm"):
    print(pd.DataFrame(res[k]["rows"], columns=res[k]["headers"]).to_string(index=False))
print(json.dumps(res["by_fault"], indent=0)[:3000])
