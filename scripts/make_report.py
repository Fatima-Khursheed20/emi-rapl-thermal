"""Build Phase-1 result tables (markdown) and figures (PNG) from results/*/summary.csv."""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
warnings.filterwarnings("ignore")

from emirapl.eval.runner import aggregate, build_method  # noqa: E402
from emirapl.eval.suite import load_suite  # noqa: E402
from emirapl.env.episode import Episode  # noqa: E402
from emirapl.llm.client import make_llm  # noqa: E402

OUT = ROOT / "docs" / "results"
# fixed colour per method (entity), reference categorical palette, never re-cycled
COLOR = {"no_recovery": "#2a78d6", "rule_table": "#eb6834", "de_retune": "#1baf7a",
         "base_agent_matched": "#eda100", "base_agent_nominal": "#e87ba4", "single_llm": "#008300"}
LABEL = {"no_recovery": "No recovery", "rule_table": "Rule table", "de_retune": "DE retune (nominal twin)",
         "base_agent_matched": "Base workflow, matched twin", "base_agent_nominal": "Base workflow, nominal twin",
         "single_llm": "Single LLM call"}
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e6e5e0"


def style(ax, title, ylabel, xlabel):
    ax.set_title(title, loc="left", fontsize=11, color=INK, weight="bold")
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_xlabel(xlabel, color=MUTED)
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#bdbcb6")
    ax.tick_params(colors=MUTED)


def load_all() -> pd.DataFrame:
    frames = []
    for f in sorted((ROOT / "results").glob("*/summary.csv")):
        if f.parent.name.startswith("_"):
            continue
        d = pd.read_csv(f)
        # parallel shards of one experiment (e.g. phase1_de_<fault>) are reported as one run
        d["run"] = "phase1_de_retune" if f.parent.name.startswith("phase1_de_") else f.parent.name
        d["method_label"] = d["method"]
        if "scripted" in f.parent.name:
            d["method_label"] = d["method"] + " (scripted proposer)"
        elif f.parent.name.startswith("phase1_llm_") and "llm" in d.columns:
            d["method_label"] = d["method"] + " [" + d["llm"].fillna("").str.split(":").str[-1] + "]"
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def line_by_mismatch(df, metric, methods, title, ylabel, fname, ymax=103):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    for m in methods:
        d = df[df.method == m]
        if d.empty:
            continue
        g = d.groupby("mismatch")[metric].mean() * 100
        ax.plot(g.index * 100, g.values, color=COLOR[m], lw=2, marker="o", ms=6,
                markeredgecolor="white", markeredgewidth=1.5, label=LABEL[m])
        ax.annotate(LABEL[m], (g.index[-1] * 100, g.values[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    style(ax, title, ylabel, "plant-model parameter mismatch (%)")
    ax.set_xticks([0, 10, 20, 30])
    ax.set_ylim(-ymax * 0.03, ymax)
    ax.set_xlim(-2, 52)
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=200)
    plt.close(fig)


def pretty(label: str) -> str:
    """Readable method names for figures, e.g. 'base_agent_nominal [openai/gpt-oss-20b]' -> 'Base workflow, nominal twin (gpt-oss-20b)'."""
    name, _, rest = label.partition(" ")
    base = LABEL.get(name, name)
    tag = rest.strip("[]() ").replace("openai/", "")
    return f"{base} ({tag})" if tag else base


def bars_llm_subset(df, subset_ids, fname):
    """Plant success of every method on the same scenarios as the LLM runs (one series -> one hue)."""
    d = df[df.scenario_id.isin(subset_ids)]
    d = d.assign(method_label=d.method_label.map(pretty))
    g = (d.groupby("method_label").plant_success.mean() * 100).sort_values()
    n = d.groupby("method_label").size().reindex(g.index)
    fig, ax = plt.subplots(figsize=(7.2, 0.42 * len(g) + 1.2))
    ax.barh(range(len(g)), g.values, color="#2a78d6", height=0.62)
    for i, (v, k) in enumerate(zip(g.values, n.values)):
        ax.text(v + 1, i, f"{v:.0f}%  (n={k})", va="center", fontsize=8, color=INK)
    ax.set_yticks(range(len(g)), g.index, fontsize=8)
    ax.set_xlim(0, 128)
    style(ax, f"Plant success on the {len(subset_ids)} LLM-run scenarios", "", "plant success (%)")
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=200)
    plt.close(fig)


def example_trajectory(suite_path, sid, methods, fname):
    sc = [s for s in load_suite(suite_path) if s.scenario_id == sid][0]
    llm = make_llm("scripted")
    z = sc.fault["zone"]
    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    for m in methods:
        res = Episode(sc).run(build_method(m, sc, llm), keep_traj=True)
        t = np.array(res.traj["t"]) / 60
        TH = np.array(res.traj["TH"])[:, z]
        ax.plot(t, TH, color=COLOR[m], lw=2, label=f"{LABEL[m]} (plant ok: {res.metrics['plant_success']})")
    ax.axhline(60, color="#e34948", lw=1.2, ls="--")
    ax.text(1, 60.4, "safety limit 60 C", fontsize=8, color=MUTED)
    ax.axvline(sc.fault["onset_s"] / 60, color="#9a9992", lw=1, ls=":")
    ax.text(sc.fault["onset_s"] / 60 + 0.5, 32, f"fault: {sc.fault['kind']} z{z} ({sc.fault['magnitude']})",
            fontsize=8, color=MUTED)
    style(ax, f"True heater temperature, zone {z} ({sid})", "temperature (C)", "time (min)")
    ax.legend(frameon=False, fontsize=7.5, loc="lower right")
    fig.tight_layout()
    fig.savefig(OUT / fname, dpi=200)
    plt.close(fig)


def main():
    import argparse
    global OUT
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT), help="output folder for tables and figures")
    OUT = Path(ap.parse_args().out)
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_all()
    md = ["# Phase-1 initial results (auto-generated by scripts/make_report.py)\n"]
    for run, d in df.groupby("run"):
        md.append(f"\n## Run `{run}` ({d.scenario_id.nunique()} scenarios)\n")
        md.append(aggregate(d, by=("method_label",)).to_markdown())
        md.append("\n\n**Plant success % by fault**\n")
        md.append((d.pivot_table(index="method_label", columns="fault", values="plant_success", aggfunc="mean") * 100)
                  .round(1).to_markdown())
        md.append("\n\n**Plant success % by mismatch**\n")
        md.append((d.pivot_table(index="method_label", columns="mismatch", values="plant_success", aggfunc="mean") * 100)
                  .round(1).to_markdown())
        md.append("\n")
    (OUT / "phase1_results.md").write_text("\n".join(md), encoding="utf-8")
    methods = [m for m in COLOR if m in set(df.method)]
    full = df[df.run.isin(["phase1_nonllm", "phase1_de_retune", "phase1_scripted_pipeline"])]  # 120-scenario suite
    line_by_mismatch(full, "plant_success", methods, "Plant success vs model mismatch", "plant success (%)",
                     "fig_plant_success_vs_mismatch.png")
    line_by_mismatch(full, "validated_but_failed", [m for m in methods if m.startswith("base_agent")],
                     "Validated by the twin, but failed on the true plant", "episodes (%)",
                     "fig_validated_but_failed.png", ymax=40)
    # compare all methods on exactly the scenarios the LLM runs have covered so far
    subset = sorted(set(df[df.run.str.startswith("phase1_llm_")].scenario_id)) or         [x.scenario_id for x in load_suite(ROOT / "configs/suites/phase1_llm_subset.json")]
    bars_llm_subset(df, subset, "fig_llm_subset_plant_success.png")
    example_trajectory(ROOT / "configs/suites/phase1_suite.json", "p1-z2-sensor_bias-mm30-s1",
                       ["no_recovery", "rule_table", "base_agent_matched", "base_agent_nominal"], "fig_example_sensor_bias.png")
    print((OUT / "phase1_results.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
