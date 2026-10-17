# EMI-RAPL Thermal

**Physics-grounded LLM agents for fault-tolerant control of a multi-zone thermal process.**
AI4015 Agentic AI semester project. Seed G3-09, *EMI-RAPL: Trustworthy Mechatronics and Robotics Intelligence through
Reasoning Agentic LLMs and Physics-Informed Learning* (supervisor: Naeem Tareen).

LLM agents supervise PI-controlled heater zones (a TCLab two-heater board, plus a four-zone furnace chain). When a
fault is detected, a Planning Agent picks a recovery mode and an Action Agent proposes setpoints, gains, output
limits or sensor offsets. Every proposal is simulated on a digital twin and checked by a deterministic validator
before it can touch the plant. Success is always judged on the **hidden true plant**, never on the twin.

The baseline re-implements the workflow of the base paper:

> J. Vyas, M. S. Gill, A. Markaj, F. Gehlhoff, M. Mercangöz, "From detection to action: Using LLM agents for
> fault-tolerant control," *Journal of Process Control*, vol. 167, 103855, 2026.

See [docs/base_paper_mapping.md](docs/base_paper_mapping.md) for the component-by-component mapping, and
[docs/architecture.png](docs/architecture.png) for the architecture (gaps G1–G3 marked).

## Quick start

```bash
# Python 3.10+; uv is optional (plain pip works too)
uv venv .venv && uv pip install -e ".[dev]"      # or: python -m venv .venv && .venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q                 # 12 tests, ~10 s, no API key needed
```

Offline run (no API key): non-LLM baselines on the 120-scenario suite:

```bash
.venv/Scripts/python scripts/run_eval.py --methods no_recovery rule_table de_retune --run phase1_nonllm
```

LLM run: copy `.env.example` to `.env` and add a free key (Gemini: https://aistudio.google.com/apikey,
Groq: https://console.groq.com/keys). Groq's free tier allows 200k tokens per day per model; runs stop cleanly at the cap and resume on the next invocation:

```bash
.venv/Scripts/python scripts/run_eval.py --provider groq --model openai/gpt-oss-20b \
    --suite configs/suites/phase1_llm_subset.json \
    --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss20b
.venv/Scripts/python scripts/run_eval.py --provider groq --model openai/gpt-oss-120b \
    --suite configs/suites/phase1_llm_subset.json \
    --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss120b
```

Gemini works the same way with `--provider gemini --model gemini-flash-latest` once a working `GEMINI_API_KEY` is set.

Check the model names against your provider's current free-tier list; model availability changes.

Results land in `results/<run>/`: `summary.csv` (one row per episode), `aggregate_by_method*.csv`, and
`episodes.jsonl` (full decision traces: prompts' outputs, validations, token counts). Runs resume where they
stopped. Run `python scripts/make_report.py` to rebuild the tables and figures in `docs/results/`.

Inspect a single decision (plan → action → twin validation → reprompts → true-plant outcome):

```bash
.venv/Scripts/python scripts/show_trace.py --run phase1_llm_gptoss20b --list
.venv/Scripts/python scripts/show_trace.py --run phase1_llm_gptoss20b --scenario p1-z2-sensor_bias-mm20-s1 --method base_agent_nominal
```

## What is in the box

| Path | Purpose |
|---|---|
| `src/emirapl/env/thermal.py` | N-zone TCLab energy-balance plant (convection, radiation, inter-zone coupling, sensor lag), RK4 |
| `src/emirapl/env/faults.py` | 5 fault types: heater degradation, enclosure heat loss, local insulation loss, sensor bias, stuck-high heater |
| `src/emirapl/env/episode.py` | episode timeline (warm-up → fault → detect → decide → apply) and true-plant metrics |
| `src/emirapl/control/pid.py` | per-zone PI loops with anti-windup and output limits |
| `src/emirapl/agents/monitor.py` | residual-based detection; oracle localisation (base-paper assumption) |
| `src/emirapl/agents/pipeline.py` | **base-paper agent**: plan → act → twin validation → reprompt (≤5) → fallback |
| `src/emirapl/tools/twin.py` | digital twin: `matched` (oracle copy), `nominal` (realistic), `calibrated` (Phase 2, G1) |
| `src/emirapl/tools/validator.py` | admissibility, ranges, safety envelope, regulation, shutdown justification |
| `src/emirapl/knowledge.py` | plant knowledge graph, mode FSM, constraints |
| `src/emirapl/contracts.py` | pydantic contracts for all agent I/O and traces |
| `src/emirapl/llm/` | OpenAI-compatible client (Gemini / Groq / Ollama / OpenAI), rate limiting, retries, token accounting; scripted client for offline tests |
| `src/emirapl/baselines/` | `no_recovery`, `rule_table`, `single_llm`, `de_retune` |
| `configs/suites/` | evaluation suites (`phase1_suite.json`: 5 faults × 2 plants × 4 mismatch levels × 3 seeds = 120) |
| `tests/` | unit + end-to-end tests |

## Methods compared

| Name | Description |
|---|---|
| `no_recovery` | PI loops left unchanged |
| `rule_table` | fixed fault-type → action table with nominal magnitudes (deterministic workflow) |
| `single_llm` | one LLM call, action applied without simulation or validation |
| `de_retune` | differential evolution over derate, PI gains and sensor offset on the nominal twin (no LLM) |
| `base_agent_matched` | base-paper workflow, twin = exact plant copy (the paper's evaluation assumption) |
| `base_agent_nominal` | base-paper workflow, twin = nominal model + fault label (realistic deployment) |

The `scripted` provider is a deterministic rule-based stand-in for the LLM. It exercises the full pipeline
offline and in CI. Its numbers are a pipeline check, not an LLM result.

## Phase-1 submission

The submitted document is [phase1/Phase1_G3-09_23I-0746.pdf](phase1/Phase1_G3-09_23I-0746.pdf) (Word source and
build scripts in `phase1/`). Handover and submission checklist: [phase1/HANDOVER_SALEHA.md](phase1/HANDOVER_SALEHA.md).

## Phase-1 results (summary)

Full 120-scenario suite. The base workflow uses a scripted proposer, so the two twins see identical proposals:

| Method | Plant success | Validated-but-failed |
|---|---|---|
| No recovery | 19.2 % | – |
| Rule table | 67.5 % | – |
| DE retune (nominal twin) | 65.0 % | – |
| Base workflow, matched twin (paper's assumption) | 80.8 % | **0.0 %** |
| Base workflow, nominal twin (realistic) | 80.8 % | **19.2 %** |

A realistic twin approves about one action in five that then fails on the true plant, mostly under sensor bias. This is
the gap that G1 targets. Real-LLM runs (gpt-oss-20b / gpt-oss-120b on Groq, 63 episodes on a 10-scenario core set
covering all five faults) show a single unvalidated LLM call succeeding in only 20–42 % of episodes, sometimes unsafely.
The validated workflow keeps the plant safe (89–100 %), but the LLM itself finds a valid action in only 56–73 % of
episodes and leans on the fallback (G2). Full tables and figures are in [docs/results/](docs/results/phase1_results.md). The
remaining LLM runs are described in [docs/phase1_remaining_llm_runs.md](docs/phase1_remaining_llm_runs.md).

## Roadmap (Phase 2)
- **G1**: adaptive EKF (joint state + parameter, EWMA noise adaptation) → calibrated twin ensemble → chance-constrained validation.
- **G2**: quantitative counterexamples + physics feasible bounds in feedback; LLM-seeded bounded DE repair.
- **G3**: diagnosis agent with residual / hypothesis-replay tools, replacing oracle localisation.
- Dashboard with human approval; optional real TCLab via `pip install -e ".[hardware]"`.

## Team
- Fatima Khursheed (23I-0746), group head
- Saleha Muhammad (23I-0727)
