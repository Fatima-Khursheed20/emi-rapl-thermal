# Base paper → this repository

Base paper: J. Vyas, M. S. Gill, A. Markaj, F. Gehlhoff, M. Mercangöz, "From detection to action: Using LLM
agents for fault-tolerant control," *Journal of Process Control* 167 (2026) 103855.
Original code (MIT): https://github.com/AISL-at-Imperial-College-London/ctrl-alt-recover

| Base paper element | Here | Notes |
|---|---|---|
| Monitoring layer (statistical references from fault-free runs) | `agents/monitor.py::ResidualMonitor` | nominal-model observer + residual/tracking/saturation/high-T symptoms, thresholds from fault-free window |
| Fault localisation supplied to agents | `agents/monitor.py::localise_oracle` | identical assumption (oracle kind + zone); replaced by the Diagnosis Agent in Phase 2 (G3) |
| CPSMod ontology + Graph RAG (GraphDB/SPARQL) | `knowledge.py::retrieve` | typed Python graph with the same knowledge categories; deterministic subgraph retrieval for the implicated zone + neighbours |
| Planning Agent (state-machine recovery path) | `agents/pipeline.py` + `llm/prompts.py::PLANNER_SYSTEM` | mode FSM: NORMAL, RETUNE, DERATE, SENSOR_CORRECTION, COMPENSATE, SAFE_SHUTDOWN |
| Action Agent (setpoint adaptation) | `llm/prompts.py::ACTION_SYSTEM`, `contracts.RecoveryAction` | setpoints, PI gains, output limits, sensor offset, shutdown |
| DPPT simulation service | `tools/twin.py::DigitalTwin` | `matched` = their evaluation assumption; `nominal` = realistic; `calibrated` = ours (G1) |
| Deterministic validation (interlocks, envelopes, dynamic feasibility) | `tools/validator.py::Validator` | admissibility, ranges, max derate, safety envelope on twin rollout, regulation band, shutdown justification |
| Reprompting with structured feedback | `agents/pipeline.py::_reprompt` | budget 5 (same as paper); feedback routed to the responsible agent |
| Deterministic fallback after budget | `agents/fallback.py` | counted as failure, as in the paper |
| Metrics: success, recovery rate, latency, tokens | `env/episode.py::evaluate`, `eval/runner.py::aggregate` | plus true-plant metrics the paper cannot compute (validated-but-failed, safety violation, retention) |

Deliberate differences: thermal multi-zone plant instead of mixer/CSTR (TCLab is the same group's earlier
testbed); Python knowledge graph instead of GraphDB; LLMs from free-tier providers (Gemini, Groq) instead of
OpenAI GPT-4o-mini / 4.1-mini.
