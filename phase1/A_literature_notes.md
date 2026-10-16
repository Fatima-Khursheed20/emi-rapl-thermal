# Deliverable A — Research notes

> **Supporting notes.** The submission document is `Phase1_G3-09_23I-0746.docx` / `.pdf` in this folder; these notes hold the underlying facts and sources.

Project: **G3-09 EMI-RAPL**, refined to **LLM-agent supervisory fault-tolerant control (FTC) of a
multi-zone thermal process** (TCLab two-heater board + 4-zone furnace chain), with physics-based
digital-twin verification.

---

## 0. Paper list (12 peer-reviewed, 2025–2026) — IEEE style

| # | Reference (IEEE) | Venue type / rank evidence |
|---|---|---|
| **1 BASE** | J. Vyas, M. S. Gill, A. Markaj, F. Gehlhoff, and M. Mercangöz, "From detection to action: Using LLM agents for fault-tolerant control," *Journal of Process Control*, vol. 167, Art. no. 103855, 2026, doi: 10.1016/j.jprocont.2026.103855. | Elsevier journal. **SJR 2025 = 0.874, Q1** (Scopus). 2025 quartiles: Q1 in Control and Systems Engineering, Industrial and Manufacturing Engineering, and Modeling and Simulation; Q2 in Computer Science Applications (screenshots in `phase 1/figures/`). SJR 0.874, h-index 138. JCR 2025: Q2 (IF 3.9). The rule accepts *Scopus or JCR* Q1, so this is eligible. Screenshot the Q1 categories as proof. |
| 2 | J. Vyas and M. Mercangöz, "Autonomous industrial control using an agentic framework with large language models," *IFAC-PapersOnLine*, vol. 59, no. 6, pp. 349–354, 2025 (14th IFAC DYCOPS), doi: 10.1016/j.ifacol.2025.07.170. | Peer-reviewed IFAC symposium proceedings |
| 3 | Y. Wang, J. Vyas, T. Liu, and M. Mercangöz, "Closed-loop control with rule-aligned small language models and multi-agent self-correction," in *Proc. IEEE Conf. Control Technology and Applications (CCTA)*, 2026, pp. 52–57, doi: 10.1109/CCTA62090.2026.11684321. | IEEE conference (peer-reviewed) |
| 4 | T. M. Arif and M. A. Rahim, "Agentic AI for real-time adaptive PID control of a servo motor," *Actuators*, vol. 14, no. 9, Art. no. 459, 2025, doi: 10.3390/act14090459. | MDPI journal (peer-reviewed) |
| 5 | N. S. M. Amin, Y.-W. Kim, and Y.-C. Byun, "Prompt-based PID tuning for adaptive AGV control via few-shot and multispeed strategies," *IEEE Access*, vol. 13, pp. 190685–190700, 2025, doi: 10.1109/ACCESS.2025.3627967. | IEEE journal |
| 6 | C. Ren, S.-M. Hong, and R. Tang, "AgentiControl-MPC: Automated model predictive control for buildings using large language model-based multi-agent system," *Advanced Engineering Informatics*, vol. 76, Art. no. 105062, Nov. 2026, doi: 10.1016/j.aei.2026.105062. | Elsevier, Q1 journal |
| 7 | W. Xin, W. Liang, and A. Chong, "Causality-constrained hierarchical LLM agents for online rule adaptation in building HVAC control," *Applied Energy*, vol. 427, Art. no. 129012, 2026, doi: 10.1016/j.apenergy.2026.129012. | Elsevier, Q1 journal. ⚠ Published online Oct. 2026, but Crossref lists the **issue as Jan. 2027**. Online-2026 normally counts; confirm with supervisor or swap for a reserve paper |
| 8 | Z. Zhou *et al.*, "LLM-guided adaptive compensator: Bringing adaptivity to robotic feedback control with large language model," *IEEE Trans. Automation Science and Engineering*, vol. 23, pp. 10762–10774, 2026, doi: 10.1109/TASE.2026.3700674. | IEEE Transactions, Q1 journal |
| 9 | C. Carr, M. Martínez-García, B. J. Marshall, M. Coombes, and Y. Zhang, "Automated UAV controller synthesis via LLM-generated control logic and particle swarm optimization," *IEEE Trans. Industrial Informatics*, vol. 22, no. 7, pp. 6187–6197, Jul. 2026, doi: 10.1109/TII.2026.3675738. | IEEE Transactions, Q1 journal |
| 10 | D. Schall, "Safe integration of large language models into industrial process control: A multi-agent architecture with P&ID-grounded validation," *Autonomous Intelligent Systems*, vol. 6, no. 1, Art. no. 14, 2026, doi: 10.1007/s43684-026-00136-1. | Springer journal |
| 11 | B. A. Galitsky and A. Rybalov, "Neuro-symbolic verification for preventing LLM hallucinations in process control," *Processes*, vol. 14, no. 2, Art. no. 322, 2026, doi: 10.3390/pr14020322. | MDPI journal |
| 12 | J. Li, S. Li, C. Martin, Z. Chen, D. Chen, and W. Li, "An LLM-assisted multi-agent control framework for roll-to-roll manufacturing systems," *Journal of Manufacturing Systems*, vol. 86, pp. 569–578, 2026, doi: 10.1016/j.jmsy.2026.04.005. | Elsevier, Q1 journal. Venue **confirmed via Crossref** (J. Manuf. Syst. 86:569–578, Jun. 2026); the arXiv version mentions NAMRC 54 |

**Foundational / supporting references (cite, but they do not count toward the 10):**
- [F1] S. Yao *et al.*, "ReAct: Synergizing reasoning and acting in language models," ICLR 2023.
- [F2] X. Guo *et al.*, "ControlAgent: Automating control system design via novel integration of LLM agents and domain expertise," arXiv:2410.19811, 2024 (preprint, the best-known LLM-control-design agent).
- [F3] J. Vyas and M. Mercangöz, "Autonomous control leveraging LLMs: An agentic framework for next-generation industrial automation," arXiv:2507.07115, 2025 (preprint; includes a **TCLab digital-twin** case study).
- [F4] J. Park, R. A. Martin, J. D. Kelly, and J. D. Hedengren, "Benchmark temperature microcontroller for process dynamics and control," *Computers & Chemical Engineering*, vol. 135, Art. no. 106736, Apr. 2020, doi: 10.1016/j.compchemeng.2020.106736 (the TCLab model we use; verified via Crossref).
- [F5] R. Storn and K. Price, "Differential evolution — a simple and efficient heuristic for global optimization," *J. Global Optimization*, 11, 1997.
- [F6] Base-paper code (MIT): github.com/AISL-at-Imperial-College-London/ctrl-alt-recover.

Reserve papers, in case the supervisor rejects one: Hu *et al.*, "AutoControl…," *Energy* 336:138329 (2025); Maher, "LLMPC," *Computers* 14(3):104 (2025); Wen *et al.*, "An experiment of using a LLM to control a water tank system," *Comput. Chem. Eng.* 211:109656 (2026); Zhang *et al.*, "LLM-driven automated design … of sliding mode controllers," *Appl. Math. Model.* 162:117204 (2026).

---

## 1. Base paper — detailed analysis notes (P1, Vyas et al., JPC 2026)

**Why this is the base paper (justification points)**
- It is the closest match to our problem: LLM agents turn fault-detection outputs into **validated** control
  actions (setpoint adaptation for PID loops) using a **digital twin** before actuation. That is the
  EMI-RAPL idea of "agents reason, physics models enforce feasibility".
- Q1 (Scopus) 2026 journal, open code (MIT), and a clear, reproducible metric set (success rate,
  recovery rate, plan/action correctness, latency, tokens). Directly usable as a comparison point.
- The same group's earlier work (P2, P3, F3) ran on the **TCLab** thermal board, which is our environment.
  So our re-implementation on TCLab physics is natural, not forced.
- Its own limitations section names exactly the gaps we target, which makes our gaps evidence-based.

**Problem.** Active FTC in process plants: after a fault is detected, choose a safe recovery path and
concrete control actions fast enough for the process dynamics.

**Method / architecture.**
- Multi-agent workflow: Monitoring → Planning Agent (chooses a state-machine recovery path) →
  Action Agent (discrete commands or continuous setpoint adaptation) → Simulation Agent (DPPT rollout) →
  Validator (deterministic checks: interlocks, envelopes, dynamic feasibility) → Reprompting loop.
- Digital Process Plant Twin (DPPT) exposes plant data, models and a simulation service.
- Graph RAG over the **CPSMod ontology** (structure, function, hybrid dynamics, control context, fault
  semantics). The graph is stored in GraphDB and queried with SPARQL.
- If no acceptable plan appears within a bounded time or the reprompt limit (5), a deterministic fallback takes over.
- LLMs: GPT-4o-mini and GPT-4.1-mini only (lightweight, single vendor).

**Data / environment.** Simulation only: (a) a discrete batch **Mixing Module** with 6 fault scenarios
(pump failure, pump degradation, clogging, sensor fault, leak, …); (b) a **CSTR** under PID regulation
with 3 faults (fouling, pump_degrade, cool_stuck_closed). 10 runs per scenario per model.

**Key results (numbers to quote)**
- Mixing: GPT-4.1-mini 60/60 success, no reprompts needed; GPT-4o-mini 51/60 (85%). Its failures cluster in
  pump_degradation (50% success, **44% recovery rate**) and sensor_fault (60% success, **33% recovery**).
  Action precision drops to 61.4% (71 false-positive actuations out of 184).
- CSTR: GPT-4.1-mini 28/30 (93.3%); GPT-4o-mini 23/30 (76.7%). On cool_stuck_closed GPT-4o-mini scored
  **4/10 with a 0% recovery rate**, because it hit the reprompt budget.
- Latency: about 2.1–3.0 s per agent call; wall-clock 33–52 s per run. Tokens: about 13–15k in per Action-Agent call (CSTR), about 55–60k per run (mixer).

**Author-stated limitations (quote these as "stated by the authors")**
- "Matched-model assumption": the DPPT used for validation is *identical* to the simulated plant,
  **including the injected fault configuration**. Plant-model mismatch and sensor noise are **not
  evaluated**. Their suggested remedy is "uncertainty-aware validation … robust envelopes, online calibration, or interval bounds".
- Fault localisation is **out of scope**; it is assumed to come from the monitoring layer. Without it, agents
  "may repeatedly propose plausible yet inapplicable actions".
- Reprompting fixes transient errors but **not systematic reasoning errors** (low recovery rates).
- Unknown/novel faults cannot be validated, because the twin only knows faults modelled a priori.
- Knowledge-graph construction effort; latencies rule out hard real-time loops; cloud LLMs only.

**Limitations we identify ourselves (critique points)**
- Success is defined as "validated LLM action applied". Because the validator twin *is* the plant, this
  metric cannot reveal **validated-but-unsafe** actions. That is a measurement blind spot, not only a scope choice.
- Only two closely related OpenAI models. No open or small models, and no cross-vendor comparison.
- n = 10 runs per scenario with no confidence intervals. Only 3 CSTR faults, all with fixed magnitudes.
- No non-LLM baselines (rule table, optimiser, or classical FTC), so the value added by the LLM is not isolated.
- The validator returns accept/revise with text feedback only. No quantitative feasibility information
  (e.g., the reachable setpoint) is given back, which may explain the systematic failures.

**How we build on / compare / go beyond**
- **Re-implement** its workflow (same agent roles, reprompt budget 5, deterministic fallback, same metrics)
  on the multi-zone thermal plant. This is baseline `base_agent`.
- **Evaluate it in two modes:** `matched` (their assumption) and `nominal` (realistic: nominal parameters
  plus the fault label only). The difference quantifies Gap 1.
- **Go beyond** with G1 (online physics calibration + uncertainty-aware validation), G2 (quantitative
  counterexample feedback + LLM-seeded numeric repair), and G3 (tool-grounded diagnosis instead of an oracle).

---

## 2. Fact sheets for papers 2–12

Fields per paper: P = problem, M = method, D = data/environment, R = results, AL = author limitations,
OL = our limitations, Rel = relevance / gap link.

### P2 — Vyas & Mercangöz, IFAC-PapersOnLine 2025 (DYCOPS)
- **P:** autonomous industrial control with LLM agents that recover from their own errors.
- **M:** operator, validator and reprompter agents (CrewAI); the validator checks whether a proposed heater action keeps the temperature in range; failed actions are revised and re-validated; a safety override kicks in after N iterations.
- **D:** **real TCLab** Arduino board; on/off heater control between 25–27 °C for 40 min. LLMs: GPT-3.5, GPT-4o-mini, GPT-4o, GPT-4.
- **R:** first-pass accuracy 60.0% (GPT-3.5) → 85.3% after reprompts; GPT-4o 99.6%. Best control (lowest mean deviation, 0.077) came from GPT-4o-mini, not the most accurate model. GPT-4 was slowest, and its latency made actions persist too long, so it had the worst time outside the band.
- **AL:** inference latency limits use to slow dynamics; simple task; the twin is embedded in the validator as a simple rule check.
- **OL:** single 40-min run per model with no repeats; on/off control only (no PID tuning or setpoints); no physics model in the validator, so "validation" is only a range check.
- **Rel:** the same TCLab environment as ours; shows latency × control-quality interaction; evidence for G1 (validator not physics-grounded) and G2 (reprompting leaves 10–15% of errors).

### P3 — Wang, Vyas, Liu, Mercangöz, IEEE CCTA 2026
- **P:** can a compact small language model (SLM) generate control actions at the edge?
- **M:** Qwen2.5-1.5B aligned with GRPO + action agent + symbolic / digital-twin-style validator + reprompting agent.
- **D:** randomised thermal-control simulations, 30 experiments × 500 steps.
- **R:** 91.5% mean action-alignment accuracy (86.3–100%); 3.84 s mean latency; 95% in-range rate under symbolic re-mapping.
- **AL:** inference latency / compute footprint at the edge (motivation); simulation only.
- **OL:** needs task-specific RL fine-tuning, so the result does not transfer to off-the-shelf small models; the validator is symbolic, with no plant-model mismatch; metric is "alignment" with a reference action rather than plant safety.
- **Rel:** shows small models need help beyond reprompting (G2). Our G2 instead targets small *untuned* free-tier models through better feedback and numeric repair.

### P4 — Arif & Rahim, Actuators 2025
- **P:** real-time LLM-based PID tuning on hardware.
- **M:** two agents in an n8n workflow: a PID Control Agent (OpenAI **o3-mini**) monitors SSE, overshoot, rise and settling time and decides when to tune; an Optimizer Agent (**GPT-4.1-mini**) proposes Kp/Ki/Kd. Two modes: guided system prompt vs free tuning "within a safe parameter range". Flask/Python link to the hardware.
- **D:** Quanser QUBE-Servo 2 (physical).
- **R:** both modes reduced IAE, ISE, MAE and RMSE after the initial transient, but were **less effective on ITAE/ITSE** because of high-frequency oscillation and noise in long runs. Table 1 reports only **3 experimental runs**, and the detailed metrics come from one of them (Run 3). Without the system prompt, the agent **failed to produce final gains in ~1 of 10 runs** (Appendix B.1).
- **AL:** a complement to classical/ML/RL control, not a replacement.
- **OL:** safety is a static gain box, with no dynamic verification before gains are applied; no classical-tuning baseline with an equal budget; very few runs (3 tabulated, 1 analysed) and no statistics; single plant; no fault scenarios.
- **Rel:** example of agentic tuning without pre-execution physics validation, which supports why our validator matters; a baseline idea for our single-call LLM method.

### P5 — Amin, Kim, Byun, IEEE Access 2025
- **P:** PID gains for AGVs without system identification.
- **M:** prompt-only in-context gain inference: MultiSpeed (interpolate by speed) and Few-Shot + MultiSpeed.
- **D:** two-wheeled AGV, 5 speeds (5–25 m/min).
- **R:** gains close to simulation-optimised ones; tracking RMSE within 5–10% of optimum; ~80% less calibration effort.
- **AL:** —
- **OL:** a single LLM call (not agentic); relies on exemplars from an existing optimiser, so it does not generalise to unseen dynamics or faults; no safety check.
- **Rel:** the non-agentic single-call baseline that we argue is insufficient under faults (agentic justification).

### P6 — Ren, Hong, Tang, Advanced Engineering Informatics 2026 (AgentiControl-MPC)
- **P:** developing building MPC is expertise-heavy.
- **M:** six specialised LLM agents (data processing, model design, MPC formulation, code generation, error correction) with inter-layer, intra-layer and state-aware communication.
- **D:** BOPTEST BESTEST Hydronic Heat Pump (simulation).
- **R:** 93.3% controller-generation success vs 66.7% for a single-agent baseline; best controller −52% energy cost and −69% discomfort vs the baseline PI controller.
- **AL:** none explicit in the abstract; read their discussion section for stated limitations.
- **OL:** a single BOPTEST test case (BESTEST Hydronic Heat Pump), so generalisation is untested; success is "a controller was generated", not safe operation; repeated runs are few; it is an offline design task with no faults or online recovery.
- **Rel:** shows the multi-agent > single-agent margin in a thermal domain (agentic justification); BOPTEST-like simulation dependence (G1).

### P7 — Xin, Liang, Chong, Applied Energy 2026
- **P:** adaptive multi-zone HVAC without building-specific models or RL training.
- **M:** hierarchical LLM agents propose hourly rule updates; a human-confirmed **causal graph** plus structural/causal checks gate updates; rule-based controllers produce 15-min setpoints.
- **D:** BOPTEST, 1-, 2- and 5-zone cases; baselines: RBCs, hierarchical MPC, PPO, MA-PPO.
- **R:** highest reward and lowest energy among all controllers; 2.2–43.2% less energy; the causal layer reduced PMV deviation and safety interventions in every case; ablations on memory, coordination and "thinking".
- **AL:** evaluated configurations only.
- **OL:** the causal graph is built manually offline; checks are structural/causal, not quantitative physics rollouts; no faults.
- **Rel:** the strongest example of rich baselines and ablations (a template for our evaluation); multi-zone thermal coupling like ours; causal constraints relate to G3's counter-hypothesis checks.

### P8 — Zhou et al., IEEE T-ASE 2026
- **P:** LLM-assisted controller design is usually tested on toy systems with no real robots.
- **M:** an LLM designs a **compensator** so an unknown system tracks a reference model (MRAC-inspired), rather than designing a controller from scratch; Lyapunov-based stability analysis.
- **D:** 2-DoF soft robot and a 1-DoF humanoid shoulder (simulation + real).
- **R:** comparable to four conventional adaptive controllers; reduced reasoning complexity vs an LLM-designed adaptive controller.
- **AL:** —
- **OL:** single-task robots; stability is argued after design, not checked online before deployment; no faults.
- **Rel:** shows adaptation to *model mismatch* is a central control problem that LLM designs must face (G1); robotics strand of EMI-RAPL.

### P9 — Carr et al., IEEE TII 2026
- **P:** program-synthesis frameworks are rarely deployed for robot control.
- **M:** the LLM synthesises the **control-law structure**; **PSO optimises the numeric coefficients** with an MDP reward; validated in PX4 SITL, then on a real UAV.
- **D:** custom UAV sim → PX4 SITL → physical UAV; lemniscate/Lissajous tracking; PID+DOB and LQR baselines.
- **R:** at least ~38% lower MSE than baselines in real flights.
- **AL:** —
- **OL:** offline design with heavy optimisation (not real-time recovery); single platform.
- **Rel:** **key evidence for G2**: separating "LLM decides structure" from "optimiser fixes numbers" works better than asking the LLM for numbers. Our numeric repair applies this inside an online recovery loop.

### P10 — Schall, Autonomous Intelligent Systems 2026
- **P:** LLM hallucination and lack of physical grounding block safety-critical use.
- **M:** 4-layer architecture with the LLM limited to an observation-only Monitor; deterministic Verification/Execution agents; P&ID graph traversal checks tag existence, actuatability, fail-state consistency and downstream impact; graduated baselines B0–B3.
- **D:** 3 Tennessee Eastman scenarios + PolyReactor + Dryer (synthetic).
- **R:** validation layer 100% recall on 43 crafted error proposals; LLMs proposed unsafe actions in 10–70% of runs (N = 50), and all of these were caught.
- **AL:** coverage limited to the evaluated failure categories and synthetic scenarios.
- **OL:** checks are **structural** (topology), not dynamic, so a physically wrong but structurally valid setpoint passes; the LLM never acts, which limits autonomy.
- **Rel:** shows how often LLMs propose unsafe actions (motivation for a validator); its validation is structural only (G1: dynamic, calibrated validation).

### P11 — Galitsky & Rybalov, Processes 2026
- **P:** LLMs give plausible but physically wrong fault explanations ("process-control hallucinations").
- **M:** the LLM (GPT-5.1) only generates explanations. A symbolic layer verifies them: Abductive Logic Programming checks coherence, counter-abduction generates rival physically-grounded hypotheses (mass/energy balance), and discourse-weighted ALP (D-ALP) weights nucleus/satellite clauses from operator notes and alarm logs (GPT-5 or an RST parser for discourse parsing).
- **D:** 500-scenario Process-Control Hallucination Dataset (pump restriction, valve stiction, fouling, runaway…).
- **R:** logical accuracy up to **+18 %**; full D-ALP gives **+15 % / +12 %** consistency gains in the ablation (depth only +7/+6, relations only +10/+9); discourse pruning cuts inference time by >20 %; a **36-person user study** shows trust **+23 %**, and clarity/trust up to ~50 %.
- **AL:** evaluation mainly on synthetic/semi-synthetic scenarios that miss real-plant noise and contingencies; quality depends on completeness of the process ontology (missing causal links give incomplete hypothesis spaces).
- **OL:** explanation-level only, with no closed-loop control or action safety; hand-built symbolic knowledge; gains are relative percentages without absolute hallucination rates in the abstract.
- **Rel:** **evidence for G3**: LLM fault diagnosis is unreliable without verification. Our diagnosis agent uses physics-residual tools plus a counter-hypothesis check.

### P12 — Li et al., J. Manufacturing Systems 2026 (roll-to-roll)
- **P:** R2R tension/velocity controller setup and adaptation need expert time.
- **M:** 5-phase LLM-assisted multi-agent framework: system ID from operating data, controller selection/tuning, **sim-to-real adaptation with safety checks**, monitoring/diagnostics, periodic model refinement.
- **D:** lab R2R system.
- **R:** 55.7% (tension) and 82.4% (velocity) RMSE reductions; beats an MPC baseline.
- **AL:** —
- **OL:** single machine; diagnosis is descriptive; how the safety checks handle model uncertainty is not quantified **[VERIFY]**.
- **Rel:** shows that online **model refinement** matters in practice. It supports G1 (the base paper lacks it) and shows a manufacturing (mechatronics) use case of EMI-RAPL.

---

## 3. Cross-paper comparison table (cell notes; reword in your own words)

| # | Title (short) | Year & venue | Dataset / env | Method / agent architecture | Metrics | Key results | Limitation / gap |
|---|---|---|---|---|---|---|---|
| **1 ★ BASE** | LLM agents for FTC | 2026, J. Process Control (Q1) | Sim: mixing module + CSTR, 9 faults | Monitor-Plan-Action-Simulate-Validate-Reprompt + Graph RAG + DPPT + fallback | success, recovery rate, plan/action correctness, latency, tokens | GPT-4.1-mini 100% / 93%; GPT-4o-mini 85% / 77%; recovery as low as 0% | matched twin; oracle localisation; reprompting can't fix systematic errors |
| 2 | Agentic industrial control | 2025, IFAC-PapersOnLine | Real TCLab, 40 min | operator / validator / reprompter (CrewAI) | first-pass & post-reprompt accuracy, time outside band | 60→85% (GPT-3.5); 99.6% (GPT-4o) | rule-based validator; single run; latency |
| 3 | SLM + self-correction | 2026, IEEE CCTA | Randomised thermal sims (30 × 500 steps) | GRPO-tuned Qwen-1.5B + validator + reprompter | action alignment, in-range rate, latency | 91.5% alignment, 3.84 s | needs RL fine-tuning; symbolic validator |
| 4 | Agentic PID servo | 2025, Actuators | Quanser QUBE-Servo 2 | o3-mini control agent + GPT-4.1-mini optimizer agent (n8n), safe gain box | IAE, ISE, MAE, RMSE, ITAE, ITSE | IAE/ISE/RMSE reduced; ITAE/ITSE not; ~1/10 unguided runs fail | 3 runs; no pre-execution verification; no classical baseline |
| 5 | Prompt PID for AGV | 2025, IEEE Access | 2-wheel AGV, 5 speeds | single-call few-shot prompting | RMSE vs optimum, calibration effort | within 5–10% of optimum; −80% effort | non-agentic; no faults/safety |
| 6 | AgentiControl-MPC | 2026, Adv. Eng. Informatics | BOPTEST heat pump | 6-agent MPC development pipeline | generation success, energy, discomfort | 93.3% vs 66.7% single agent; −52% cost | offline design; sim-only; success ≠ safe operation |
| 7 | Causality-constrained HVAC agents | 2026, Applied Energy | BOPTEST 1/2/5-zone | hierarchical LLM agents + causal-graph gating | reward, energy, PMV·h, interventions | −2.2 to −43.2% energy | manual causal graph; no quantitative physics rollout; no faults |
| 8 | LLM adaptive compensator | 2026, IEEE T-ASE | Soft robot, humanoid shoulder (sim + real) | LLM-designed MRAC-style compensator + Lyapunov analysis | tracking error vs adaptive controllers | comparable to 4 adaptive controllers | offline; no online verification/faults |
| 9 | LLM + PSO UAV control | 2026, IEEE TII | UAV sim → PX4 SITL → real UAV | LLM synthesises law, PSO tunes coefficients | MSE on trajectories | ≥38% lower MSE (real) | offline, compute-heavy |
| 10 | P&ID-grounded validation | 2026, Autonomous Intelligent Systems | TEP + 2 synthetic plants | observation-only LLM + deterministic verifier (graph traversal) | recall of invalid proposals, unsafe-proposal rate | 100% recall; LLM unsafe 10–70% | structural checks only; no dynamics |
| 11 | Neuro-symbolic hallucination check | 2026, Processes | 500-scenario hallucination dataset + 36-user study | GPT-5.1 generator + ALP + counter-abduction + discourse weighting | logical accuracy, consistency, inference time, trust | accuracy +18 %; consistency +15/+12 %; trust +23 % | explanation only; synthetic data; ontology-dependent |
| 12 | LLM multi-agent R2R control | 2026, J. Manuf. Syst. | Lab R2R machine | 5-phase: sys-ID, tuning, sim-to-real w/ safety, monitoring, refinement | RMSE tension / velocity | −55.7% / −82.4% RMSE; beats MPC | single machine; uncertainty in safety checks not quantified |

---

## 4. Candidate gaps (≥3 required; the 3 selected are marked ✔)

1. ✔ **G1 — Validation assumes a perfect (matched) twin.** Evidence: P1 matched-model assumption and untested mismatch/noise; P2 and P3 validators are rule/symbolic only; P10 structural only; P6/P7 simulation-only; P12 and P8 show model refinement/adaptation matters.
2. ✔ **G2 — Pass/fail reprompting cannot repair systematic numeric errors, especially for small/cheap models.** Evidence: P1 recovery 0–44% for GPT-4o-mini, budget exhaustion; P2 leaves 15% errors after reprompts with GPT-3.5; P3 needs RL fine-tuning to make an SLM reliable; P9 shows LLM-structure + optimiser-numbers beats LLM-only numbers.
3. ✔ **G3 — Fault localisation is assumed (oracle) and LLM diagnosis is unverified.** Evidence: P1 localisation out of scope, and agents fail without it; P11 LLM fault explanations hallucinate; P10 confines the LLM to observation because of hallucination; P7 needs causal constraints to stabilise LLM decisions.
4. (not selected) **Timeliness:** LLM latency (2–50 s) vs process dynamics (P1, P2, P3). This is relevant, but we use it as a measured system metric instead.
5. (not selected) **Statistical weakness:** ≤10 runs, no confidence intervals, few baselines (P1, P2, P4, P6). We address this in methodology rather than as a gap.
6. (not selected) **Knowledge-graph construction cost** (P1, P7). Out of semester scope.

Gap table: see `B_proposal_notes.md §4` (same rows, with approach + measurement).
