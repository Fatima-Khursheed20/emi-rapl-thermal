# Deliverable B — Proposal notes

> **Supporting notes.** The submission document is `Phase1_G3-09_23I-0746.docx` / `.pdf` in this folder; these notes hold the underlying facts and sources.

## 1. Title & selected seed
- First page: project code **G3-09**, title, Fatima Khursheed (23I-0746, group head), Saleha Muhammad (23I-0727). File name: **Phase1_G3-09_23I-0746.pdf**.
- Seed: **G3-09 EMI-RAPL: Trustworthy Mechatronics and Robotics Intelligence through Reasoning Agentic LLMs and Physics-Informed Learning** (supervisor: Naeem Tareen).
- Scope refinement required by the seed: "select one robot/mechatronics task; combine physics constraints with agent reasoning; validate on hardware or a high-fidelity digital twin". Our task: **fault-tolerant supervisory control of a multi-zone electric thermal process** (the seed's multi-zone furnace / adaptive PID / adaptive EKF thrust).
- Working title options (pick or adapt):
  - *"Mind the Twin Gap: Physics-Calibrated, Uncertainty-Aware LLM Agents for Fault-Tolerant Multi-Zone Thermal Control"*
  - *"EMI-RAPL-Thermal: Trustworthy LLM Agents with Online Physics Calibration for Fault-Tolerant Furnace Control"*

## 2. Problem & motivation
- Real problem: multi-zone thermal processes (industrial furnaces, heat-treatment ovens, reflow ovens, the TCLab teaching rig) suffer actuator degradation, insulation/heat-loss changes, sensor bias, and stuck heaters. Operators must pick a recovery mode (derate, retune, correct a sensor, shut down) quickly, without overheating product or equipment.
- Target users: process/control engineers and operators of small-to-medium thermal equipment (SMEs, labs), the same audience the seed names.
- Current limitation: LLM-agent FTC (base paper) validates actions on a twin that is assumed identical to the plant, with the fault already localised. In practice the twin is wrong (mismatch, noise) and the fault is unknown, so "validated" actions can still be unsafe.
- Why it matters: a validator that trusts a wrong model gives false assurance. Safety violations or unnecessary shutdowns cost equipment and production.

## 3. Base paper & how we go beyond
- Base: Vyas et al., *J. Process Control* 167 (2026) 103855 (see A-notes §1).
- Build on: re-implement its agent roles, validation-reprompt loop, fallback and metrics on our plant (`base_agent`).
- Compare against: same scenarios, same metrics, same reprompt budget, both in its own matched-twin setting and in a realistic nominal-twin setting.
- Go beyond: G1 calibrated, uncertainty-aware twin; G2 physics counterexample feedback + numeric repair; G3 verified diagnosis instead of oracle localisation.

## 4. Gap table (fill the "Supporting evidence" column with your own phrasing)

| Gap | Supporting evidence | Proposed approach | How it will be measured |
|---|---|---|---|
| **G1** Validation assumes a matched twin; mismatch/noise untested | P1 (states matched-model assumption; mismatch & noise not evaluated); P2, P3 (rule/symbolic validators); P10 (structural checks only); P12, P8 (model refinement/adaptation needed in practice) | Adaptive EKF jointly estimates zone temperatures + heater gains α, heat-loss U and sensor bias, with EWMA noise adaptation (seed thrust 1). Twin = calibrated parameters; validation over an **ensemble sampled from the EKF covariance**; accept only if the 95th-percentile max T ≤ limit and regulation holds (chance constraint) | **Validated-but-failed rate** (validated by twin, unsafe/unregulated on true plant), plant success %, safety-violation % at mismatch 0/10/20/30 % and 2 noise levels; parameter RMSE of the EKF; added latency |
| **G2** Pass/fail reprompting cannot fix systematic numeric errors, esp. small LLMs | P1 (recovery 0–44 % for GPT-4o-mini; reprompt-budget exhaustion); P2 (15 % errors remain after reprompts); P3 (needs GRPO fine-tuning); P9 (LLM structure + optimiser numbers works) | Validator returns **quantitative counterexamples + physics feasible bounds** (e.g., max reachable steady temperature per zone from the calibrated energy balance, minimum derate). If the mode is right but numbers fail, a **bounded DE repair seeded with the LLM proposal** runs inside that mode | Recovery rate (successful / needing reprompt), mean reprompts, fallback %, plant success with the **small** model (gpt-oss-20b) vs the large one (gpt-oss-120b); tokens & wall time |
| **G3** Fault localisation assumed (oracle); LLM diagnosis unverified | P1 (localisation out of scope; failures without it); P11 (LLM fault explanations hallucinate); P10 (LLM confined to observation); P7 (causal constraints needed) | **Diagnosis agent** with tools: EKF parameter-deviation report, innovation tests, fault-hypothesis replay (likelihood of recent data under each candidate fault on the twin), plus a counter-hypothesis check before committing; outputs a ranked FaultReport | Top-1 localisation accuracy (kind + zone), end-to-end plant success **without oracle** vs base with oracle and base without oracle; misdiagnosis-induced unsafe actions |

## 5. Target system (end of semester)
- A runnable **EMI-RAPL-Thermal supervisor**: Python package + CLI + a small dashboard (Streamlit, Phase 2) showing live zone temperatures, alarms, the agent's decision trace (plan → action → twin prediction → validation), and approve/override buttons.
- Runs against the simulated plant (2-zone TCLab, 4-zone furnace) or, unchanged, against a **real TCLab board** through the `tclab` package (optional hardware, ~USD 35).
- Reproducible benchmark: scenario suite + evaluation scripts + all baselines.

## 6. Agentic justification (points)
- The fault is not known in advance: kind, zone and magnitude vary, and some faults need opposite responses (a stuck-high heater on a hot zone needs shutdown; on a cool zone it does not). A fixed fault→action table (our `rule_table` baseline) fails when the true magnitude differs from the assumed one.
- The decision needs **multi-step tool use with feedback**: diagnose (residual tools), consult knowledge (admissible modes), propose, simulate on a twin, read violations, revise. A single LLM call cannot see the consequence of its own proposal.
- **Environment interaction** is essential: the twin rollout result changes the next action. A RAG pipeline only retrieves text and cannot check physics.
- A deterministic optimiser alone (our `de_retune` baseline) needs a pre-defined decision space and objective per fault and has no mode reasoning. The agent picks the mode and decision space; the optimiser is a tool inside it (G2).
- Human control is part of the loop: shutdowns and large derates need approval.

## 7. Goals & success criteria
- Development objectives
  1. Multi-zone thermal digital twin with fault injection, mismatch and noise ✔ (Phase 1, done)
  2. Base-paper agent re-implementation + 4 baselines ✔ (Phase 1, done)
  3. Adaptive EKF calibration + uncertainty ensemble validation (G1)
  4. Counterexample feedback + LLM-seeded repair (G2)
  5. Diagnosis agent with residual/hypothesis tools (G3)
  6. Dashboard with human approval + trace viewer; optional TCLab hardware run
- Research success criteria (one or more per gap)
  - G1: validated-but-failed ≤ 5 % at 30 % mismatch (vs base-nominal), and plant success ≥ base-nominal + 15 percentage points.
  - G2: with gpt-oss-20b, recovery rate ≥ 80 % and mean reprompts −40 % vs the base workflow.
  - G3: top-1 localisation ≥ 85 %; end-to-end plant success without oracle within 10 pp of the base agent *with* oracle.

## 8. Data / environment / source (CONFIRMED)
- Physics model: TCLab energy balance (Park, Martin, Kelly, Hedengren, Comput. Chem. Eng. 2020): convection + radiation to ambient, inter-heater coupling, first-order sensor lag. Verified in code: full power settles at ~71 °C / ~62 °C (heater 1 / 2), matching the real board.
- Plants: 2-zone (TCLab board) and 4-zone chain (multi-zone furnace).
- True plant ≠ model: multiplicative mismatch on U, α, τ_s, m (0, 10, 20, 30 %), measurement noise σ = 0.15 °C, 0.01 °C quantisation.
- Five fault types (actuator, process, sensor): heater_degradation (α × 0.3–0.5), heat_loss_increase (U × 2.5–3.5, enclosure-wide), local_insulation_loss (U_z × 3–5), sensor_bias (−7 to −14 °C), actuator_stuck_high (85–100 %).
- Evaluation suite: `configs/suites/phase1_suite.json`, **120 scenarios** = 5 faults × 2 plant sizes × 4 mismatch levels × 3 seeds. Phase 2 extends this to 5 seeds, 2 noise levels, and a held-out set of unseen magnitudes and compound faults.
- LLM sources (confirmed working): **Groq free tier, `openai/gpt-oss-20b` (small) and `openai/gpt-oss-120b` (large)**, through the OpenAI-compatible API with low reasoning effort. Limits: 8k tokens/min and 1,000 requests/day per model. Gemini is currently blocked for our Google project (403); a new AI Studio key is optional. Local Ollama is the fallback.

## 9. System architecture (components)
- Models: Planning, Action and Diagnosis agents (LLM); deterministic monitor, validator, fallback, PI loops.
- Tools: `snapshot`, `retrieve(knowledge subgraph)`, `twin.rollout(action)`, `validate(action)`, Phase 2: `ekf.estimate()`, `feasible_bounds(zone)`, `test_hypothesis(kind, zone)`, `repair(action)`.
- State/context: pydantic contracts `Snapshot`, `FaultReport`, `PlanDecision`, `RecoveryAction`, `ValidationResult`, `LLMCallRecord`, `DecisionTrace` (all in `src/emirapl/contracts.py`).
- Knowledge: typed plant knowledge graph (structure, dynamics, mode FSM, admissible modes per fault class, constraints). This is our lightweight analogue of the base paper's CPSMod/GraphDB.
- Memory: per-episode decision trace (conversation + validations); no long-term memory needed.
- Orchestration: explicit state machine (plan → act → validate → reprompt / fallback), budget 5.
- Human controls: approval of SAFE_SHUTDOWN and large derates; manual override; full audit trace.
- External environment: simulated plant or real TCLab.
- Diagram: `emi-rapl-thermal/docs/architecture.png` (also .svg / .pdf). Gaps G1–G3 are marked in orange; the baseline path is in blue.

## 10. Baselines
- B0 `no_recovery`: PI loops unchanged.
- B1 `rule_table`: deterministic fault-type → action table with nominal magnitudes (non-agentic workflow).
- B2 `single_llm`: one LLM call, applied without simulation/validation.
- B3 `de_retune`: differential evolution over derate + PI gains (+ sensor offset) on the nominal twin (non-LLM optimiser; the seed's DE line).
- B4 `base_agent_matched` / `base_agent_nominal`: base-paper workflow with an oracle twin (its own assumption) / a realistic nominal twin.

## 11. Research questions & hypotheses
- **RQ1 (G1):** Under 10–30 % plant-model mismatch, does validating on an EKF-calibrated twin ensemble reduce the rate of validated-but-unsafe or unregulated actions compared with the base workflow's nominal twin?
  **H1:** At 30 % mismatch, validated-but-failed drops to ≤ 5 % and plant success rises by ≥ 15 pp, with ≤ 2× decision wall time.
- **RQ2 (G2):** Does returning quantitative counterexamples and feasible bounds, plus LLM-seeded numeric repair, raise the recovery rate of a small free-tier LLM?
  **H2:** For gpt-oss-20b, recovery rate ≥ 80 % (base workflow lower) and mean reprompts reduced by ≥ 40 %.
- **RQ3 (G3):** Can a tool-grounded diagnosis agent replace oracle localisation without losing end-to-end safety?
  **H3:** Top-1 localisation ≥ 85 %, and plant success without oracle within 10 pp of the oracle-localised base agent.

## 12. Evaluation plan
- Sets: Phase-1 suite (120), Phase-2 extended suite (~200 + held-out). Each LLM configuration is repeated 3× (temperature 0.2), reporting mean ± 95 % CI.
- Metrics: plant success, agent success (base definition), validated-but-failed, safety violation (> 0.5 °C or > 60 s above 60 °C after the action), max T, time above limit, setpoint retention, IAE, recovery rate, reprompts, fallback %, LLM calls, tokens, LLM latency, decision wall time, localisation accuracy (G3), EKF parameter RMSE (G1).
- Comparisons: all baselines on the same scenarios; per-fault and per-mismatch breakdowns.
- Ablations: G1 {nominal twin, EKF point estimate, EKF ensemble}; G2 {pass/fail text, + quantitative violations, + feasible bounds, + repair}; G3 {oracle, symptoms only, + residual tools, + counter-hypothesis}; LLM size {gpt-oss-20b, gpt-oss-120b} (+ Gemini if access is restored).
- Statistics: paired comparisons per scenario (McNemar for success rates; Wilcoxon for continuous metrics).

## 13. Milestones, risks, fallback
- Phase 2 (15 days): D1–3 EKF + calibrated twin (G1); D4–6 counterexample feedback + repair (G2); D7–9 diagnosis agent (G3); D10–12 full experiments + ablations; D13–15 dashboard, failure analysis, paper. Phase 3 (1 week): slides, demo, viva prep.
- Risks → fallback:
  - Free-tier rate limits (Groq: 8k tokens/min, 1k requests/day per model) → token-budget pacer in the client (implemented), two models run in parallel on separate quotas, a 2-zone subset for repeated LLM runs, local Ollama as a last resort. Gemini access blocked → not needed; optional new key.
  - LLM nondeterminism → 3 repeats, CIs, fixed temperature, logged prompts.
  - EKF divergence for large mismatch → recursive least-squares / batch grey-box fit as fallback estimator.
  - DE compute (~30–130 s per decision) → smaller population, shorter horizon, vectorised rollouts.
  - No hardware → TCLab physics model with published parameters; optional real-board run if purchased.

## 14. Work division (2 members) — swap the split if you prefer
- **Fatima Khursheed (23I-0746), group head:** physics/twin, adaptive EKF + ensemble validation (G1), diagnosis tools (G3), evaluation harness and statistics.
- **Saleha Muhammad (23I-0727):** agent prompts and orchestration, counterexample feedback + repair (G2), diagnosis agent reasoning (G3), dashboard, LLM provider experiments.
- Both: literature review, paper writing, failure analysis. Both must understand the whole system (viva). Make sure **both** of you commit to GitHub.

## 15. Publication direction
- Contribution: (i) first quantification of the **validation–reality gap** of LLM FTC agents under plant-model mismatch; (ii) a calibrated, uncertainty-aware validator that closes it; (iii) evidence that numeric repair makes small open models viable; (iv) an open multi-zone TCLab FTC benchmark.
- Venues: IFAC World Congress / DYCOPS / ADCHEM workshop papers, IEEE CCTA, *Computers & Chemical Engineering*, *Journal of Process Control*.

## 16. Phase-1 evidence already observed (qualitative; use as failure cases)
- **Twin wrongly rejects a correct action (G1).** In `p1-z2-sensor_bias-mm20-s1`, gpt-oss-20b inferred a +7.5 °C offset from the residual (true bias −7.7 °C). The nominal twin assumes −10 °C, so it rejected the correct action 5× and the episode ended in fallback.
- **Systematic mode error that reprompting cannot fix (G2).** In `p1-z2-heater_degradation-mm00-s0`, the planner chose RETUNE for a degraded heater whose setpoint is physically unreachable (twin: 100 % output, 2.4 °C short). Feedback goes to the Action Agent, which can only change gains (Kc 6→10→20), so the episode ends in fallback. A feasible bound such as "max reachable 47.6 °C" would point to DERATE.
- Print either case with `python scripts/show_trace.py --run <run> --scenario <id> --method <method>`.

## 17. Phase-1 initial results
- See `C_initial_results.md` (generated from `emi-rapl-thermal/results/`).
