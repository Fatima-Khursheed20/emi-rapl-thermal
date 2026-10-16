"""Draw the system architecture diagram (baseline vs proposed, gaps marked).

Grid layout: 5 columns x 3 rows, orthogonal arrow routing so flows never cross boxes.
"""
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).resolve().parents[1] / "docs"
FILL = {"base": "#dbe9f6", "new": "#fde2c8", "env": "#e3f1df", "det": "#eeeeee", "hum": "#f3e1f3"}
EDGE = {"base": "#2f6db3", "new": "#d9771f", "env": "#3f8f3a", "det": "#666666", "hum": "#9b4f9b"}
COL = [2, 32, 62, 92, 122]  # column x origins, width 26
W = 23
ROW = {1: 4, 2: 30, 3: 55}  # row y origins
H = 16

fig, ax = plt.subplots(figsize=(15, 9.6))
ax.set_xlim(-1, 150)
ax.set_ylim(0, 96)
ax.axis("off")


def box(col, row, title, body, kind="base", tag=None, span=1):
    x, y, w = COL[col], ROW[row], W * span + (COL[1] - COL[0] - W) * (span - 1)
    ax.add_patch(FancyBboxPatch((x, y), w, H, boxstyle="round,pad=0.3,rounding_size=1.2",
                                fc=FILL[kind], ec=EDGE[kind], lw=1.6))
    ax.text(x + w / 2, y + H - 1.6, title, ha="center", va="top", fontsize=9.5, weight="bold")
    ax.text(x + w / 2, y + H - 5.0, body, ha="center", va="top", fontsize=7.5, linespacing=1.3)
    if tag:
        ax.text(x + w - 0.5, y + H + 0.5, tag, ha="right", va="bottom", fontsize=9, weight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.25", fc=EDGE["new"], ec="none"))


def path(pts, label="", color="#333", ls="-", lpos=None, rot=0, fs=7.3):
    for (x0, y0), (x1, y1) in zip(pts[:-2], pts[1:-1]):
        ax.plot([x0, x1], [y0, y1], color=color, lw=1.3, ls=ls, solid_capstyle="round")
    ax.annotate("", xy=pts[-1], xytext=pts[-2],
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.3, ls=ls, mutation_scale=11,
                                shrinkA=0, shrinkB=0))
    if label:
        if lpos is None:
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            lpos = ((x0 + x1) / 2, (y0 + y1) / 2 + (2.4 if y0 == y1 else 0))
        ax.text(*lpos, label, fontsize=fs, ha="center", va="center", color=color, rotation=rot,
                bbox=dict(fc="white", ec="none", pad=0.5, alpha=0.95))


ax.text(75, 94.5, "EMI-RAPL Thermal: physics-calibrated LLM agents for fault-tolerant multi-zone thermal control",
        ha="center", fontsize=12.5, weight="bold")

# ---- row 3: reasoning
box(0, 3, "Diagnosis Agent (LLM)", "tools: EKF parameter deviation,\ninnovation tests, hypothesis\nreplay on twin, counter-check\n(baseline: ORACLE kind + zone)", "new", "G3")
box(1, 3, "Knowledge retrieval", "plant knowledge graph:\nstructure, dynamics,\nmode FSM, constraints\n(Graph-RAG analogue)")
box(2, 3, "Planning Agent (LLM)", "selects ONE target mode\nfrom the admissible set\n(e.g. DERATE, RETUNE,\nSENSOR_CORR., SHUTDOWN)")
box(3, 3, "Action Agent (LLM)", "proposes setpoints,\nPI gains, q_max,\nsensor offsets, shutdown\n(JSON contract)")
box(4, 3, "Numeric repair", "physics feasible bounds +\ncounterexample feedback;\nLLM-seeded bounded DE\ninside the chosen mode", "new", "G2")

# ---- row 2: verification / control
box(0, 2, "Human operator", "approves SAFE_SHUTDOWN\nand large derates;\nmanual override;\nreads decision trace", "hum")
box(1, 2, "Fallback policy", "deterministic derate,\nor shutdown if twin\npredicts unsafe hold\n(= agent failure)", "det")
box(2, 2, "Reprompter", "violations -> structured\nrevision prompt to the\nresponsible agent\n(budget = 5)")
box(3, 2, "Validator", "admissibility + ranges\nsafety: max T <= 60 C\nregulation band\nshutdown justification\nG1: chance constraint")
box(4, 2, "Digital twin (DPPT)", "rollout of candidate action\nbaseline: matched (oracle)\nor nominal parameters\nG1: calibrated ensemble")

# ---- row 1: plant side
box(0, 1, "Monitoring layer", "nominal-model observer;\nresidual, tracking,\nsaturation, high-T\n(fault-free references)", "det")
box(1, 1, "Low-level PI loops", "PI loop per zone, 1 Hz\nanti-windup, limit q_max\nsensor-offset correction\nmaster heater relay", "det")
box(2, 1, "Physical process (true plant)", "multi-zone thermal plant, TCLab energy balance\n(2-zone TCLab board / 4-zone furnace chain)\n"
    "hidden: 0-30 % parameter mismatch, sensor noise\nfault injector: 5 fault types | optional real TCLab", "env", span=2)
box(4, 1, "Adaptive EKF calibration", "joint state + parameter\n(heater gain, heat loss,\nbias); EWMA noise adapt.\n-> mean + covariance", "new", "G1")

# ---- flows (orthogonal)
cx = [c + W / 2 for c in COL]
r1t, r2b, r2t, r3b = ROW[1] + H, ROW[2], ROW[2] + H, ROW[3]
mid3, mid2, mid1 = ROW[3] + H / 2, ROW[2] + H / 2, ROW[1] + H / 2
path([(COL[1], mid1 + 2), (COL[0] + W, mid1 + 2)], "y, u, SP")
path([(COL[2], mid1 + 2), (COL[1] + W, mid1 + 2)], "y")
path([(COL[1] + W, mid1 - 3), (COL[2], mid1 - 3)], "heater %")
path([(COL[0] + 1, ROW[1] + H), (COL[0] + 1, ROW[1] + H + 2), (-0.5, ROW[1] + H + 2), (-0.5, mid3), (COL[0], mid3)],
     "alarm + symptoms", lpos=(-0.5, 46), rot=90)
path([(COL[0] + W, mid3), (COL[1], mid3)], "FaultReport")
path([(COL[1] + W, mid3), (COL[2], mid3)], "subgraph")
path([(COL[2] + W, mid3), (COL[3], mid3)], "mode")
path([(COL[3] + W, mid3), (COL[4], mid3)], "proposal", color=EDGE["new"], ls="--")
path([(cx[3], r3b), (cx[3], r2t)], "candidate action")
path([(cx[4], r3b), (cx[4], r3b - 3), (COL[3] + W - 2, r3b - 3), (COL[3] + W - 2, r2t)], "repaired action",
     color=EDGE["new"], ls="--", lpos=(COL[4] + 2, r3b - 3))
path([(COL[3] + W, mid2 + 3), (COL[4], mid2 + 3)], "rollout")
path([(COL[4], mid2 - 3), (COL[3] + W, mid2 - 3)], "trajectory")
path([(COL[3] + W, ROW[1] + H - 6), (COL[4] - 0.5, ROW[1] + H - 6)], "y, u", color=EDGE["new"], ls="--",
     lpos=(COL[3] + W + 3.5, ROW[1] + H - 3.6))
path([(cx[4], r1t), (cx[4], r2b)], "params + covariance", color=EDGE["new"], ls="--")
path([(COL[3], mid2), (COL[2] + W, mid2)], "fail: violations")
path([(cx[2] - 6, r2t), (cx[2] - 6, r3b)], "re-plan")
path([(cx[2] + 6, r2t), (cx[2] + 6, r3b - 2.5), (COL[3] - 1, r3b - 2.5), (COL[3] - 1, r3b)], "revise", lpos=(cx[2] + 9.5, r3b - 2.5))
path([(COL[2], mid2), (COL[1] + W, mid2)], "budget hit")
path([(cx[3] + 4, r2b), (cx[3] + 4, r2b - 3.5), (cx[1] + 6, r2b - 3.5), (cx[1] + 6, r1t)], "pass: apply validated action",
     color=EDGE["hum"], lpos=(cx[2] + 6, r2b - 3.5))
path([(cx[1] - 4, r2b), (cx[1] - 4, r1t)], "fallback", color="#666")
path([(COL[0] + W - 4, r2b), (COL[0] + W - 4, r2b - 3.5), (cx[1] + 5.5, r2b - 3.5)], "approve / override",
     color=EDGE["hum"], ls=":", lpos=(COL[0] + 11, r2b - 3.5))

# ---- top band: shared state + legend
ax.add_patch(FancyBboxPatch((COL[0], 76), 146, 6, boxstyle="round,pad=0.3,rounding_size=1.0", fc="#f7f7f7", ec="#999"))
ax.text(75, 79, "Shared state & audit trace (pydantic contracts): Snapshot | FaultReport | PlanDecision | RecoveryAction | "
        "ValidationResult | LLMCallRecord | DecisionTrace  ->  JSONL trace + metrics", ha="center", va="center", fontsize=8.2)
items = [("base", "Base-paper workflow (Vyas et al., JPC 2026) = baseline"), ("new", "Proposed components for G1-G3 (dashed = new flow)"),
         ("det", "Deterministic module"), ("env", "Environment"), ("hum", "Human control")]
x = COL[0]
for k, lab in items:
    ax.add_patch(FancyBboxPatch((x, 86), 3, 2, boxstyle="round,pad=0.1", fc=FILL[k], ec=EDGE[k]))
    ax.text(x + 4, 87, lab, fontsize=8, va="center")
    x += 4 + len(lab) * 0.78 + 3
ax.text(75, 91.3, "Baseline: Monitor > Oracle > KB > Planner > Action > twin (matched | nominal) > Validator > Reprompt / Fallback      "
        "Proposed: Monitor > Diagnosis (G3) > KB > Planner > Action > Repair (G2) > calibrated twin ensemble (G1) > Validator",
        ha="center", fontsize=7.8, style="italic")

OUT.mkdir(exist_ok=True)
for ext in ("png", "svg", "pdf"):
    fig.savefig(OUT / f"architecture.{ext}", dpi=200, bbox_inches="tight")
print("saved", OUT / "architecture.png")
