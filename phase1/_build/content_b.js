// Deliverable B content (proposal). Results narrative lives in results_text.js (written after the runs).
module.exports.TITLE = 'Mind the Twin Gap: Physics-Calibrated, Uncertainty-Aware LLM Agents for Fault-Tolerant Multi-Zone Thermal Control';

module.exports.SEED = [
  'Selected project: G3-09, "EMI-RAPL: Trustworthy Mechatronics and Robotics Intelligence through Reasoning Agentic LLMs and Physics-Informed Learning" (supervisor: Naeem Tareen). The seed describes a broad programme spanning WAAM process identification, adaptive PID control of multi-zone furnaces, adaptive extended Kalman filtering, RLHF for robotic tasks and inverse kinematics, and it asks each group to select one robot or mechatronics task, combine physics constraints with agent reasoning, and validate on hardware or a high-fidelity digital twin.',
  'We selected the seed\'s first thrust, physics-grounded process control of multi-zone thermal systems, and refined it into one concrete problem: supervisory fault-tolerant control of a multi-zone electric heating process, in which LLM agents choose and parameterise recovery actions and a physics-based digital twin, calibrated online by an adaptive EKF, decides whether those actions are safe. The adaptive-PID, differential-evolution and adaptive-EKF elements of the seed reappear as the low-level control loops, an optimisation tool and the calibration module respectively.',
];

module.exports.PROBLEM = [
  'Multi-zone thermal equipment such as heat-treatment furnaces, reflow ovens and curing ovens is regulated by one temperature loop per zone. Faults are common and varied: heating elements age and deliver less power, insulation degrades or a door seal fails and heat loss rises, thermocouples drift and read low, and a failed relay can leave a heater stuck on. Each fault calls for a different response. A degraded zone needs a lower, reachable setpoint; a biased sensor needs correcting before the loop overheats the product; a stuck heater may need the neighbouring zones switched off or, if the zone would exceed its limit regardless, a full shutdown. Choosing correctly requires reasoning about the specific fault and its size, while a wrong choice either damages product and equipment or stops production unnecessarily.',
  'Target users are process and control engineers and operators of small and medium thermal equipment, including SMEs and teaching laboratories, the audience the EMI-RAPL seed aims to serve. These users rarely have a dedicated fault-tolerant control system and depend on fixed alarm responses or manual intervention.',
  'Recent work shows that LLM agents can propose recovery actions that are then checked on a digital twin before execution [1]. However, that evaluation assumes the twin is an exact copy of the plant, including the injected fault, and that the fault has already been located. In practice the twin is only a nominal model, the fault size is unknown, and the monitor reports symptoms rather than causes. Under these conditions a twin can approve an action that fails on the real plant or reject one that would have worked. This false assurance is the core problem our project addresses: making the verification step trustworthy when the model is wrong, and making the agent able to recover when verification fails.',
];

module.exports.BASE_GAPS = [
  'The base paper, Vyas et al. [1] (Journal of Process Control, 2026, Scopus Q1), proposes a monitoring, planning, action, simulation, validation and reprompting workflow for fault-tolerant control, grounded in an ontology through Graph RAG and protected by a deterministic validator and fallback. It reports 85–100% success with lightweight GPT models on two simulated process benchmarks. Section A.2 analyses it in detail.',
  'Our project builds on it in three steps. First, we re-implement the workflow on a multi-zone thermal plant and evaluate it in its own matched-twin setting and in a realistic nominal-twin setting, which turns its main unstated risk into a measured quantity. Second, we address the three gaps selected in Section A.5, one component each: an EKF-calibrated, uncertainty-aware twin (G1); quantitative counterexample feedback with LLM-seeded numeric repair (G2); and a diagnosis agent that removes the oracle localisation (G3). Third, we judge every method on the hidden true plant and compare against non-LLM baselines, which the base paper does not do.',
];

module.exports.TARGET = [
  'By the end of the semester the project will deliver EMI-RAPL Thermal, a working supervisory agent for multi-zone thermal processes, consisting of:',
];
module.exports.TARGET_BULLETS = [
  'A Python package and command-line tool that connects to the simulated plant (two-zone TCLab board or four-zone furnace chain) or, through the same interface, to a real TCLab board via the tclab package.',
  'The full agent: diagnosis, knowledge retrieval, planning, action synthesis, numeric repair, calibrated-twin validation, reprompting and fallback, with every decision stored as an auditable trace.',
  'A small dashboard showing live zone temperatures, alarms and each decision (plan, proposed action, twin prediction, verdict), with buttons for the operator to approve a shutdown or large derate, or to override.',
  'A reproducible benchmark: scenario suites, all baselines, evaluation scripts and the scripts that regenerate every table and figure in the final paper.',
];

module.exports.AGENTIC = [
  ['The fault is unknown in advance.', 'Kind, zone and magnitude vary, and the right response depends on all three; a stuck heater on a hot zone needs a shutdown, the same fault on a cooler zone does not. A fixed fault-to-action table (our rule-table baseline) uses assumed magnitudes and fails when reality differs.'],
  ['The decision requires a feedback loop with the environment.', 'The agent must diagnose with residual tools, consult admissible modes, propose, simulate the proposal on the twin, read the violations, and revise. A single LLM call cannot see the consequence of its own proposal; our single-call baseline applies whatever it proposes.'],
  ['Retrieval alone cannot check physics.', 'A RAG pipeline can recall what a fault means, but only a rollout on a calibrated model can show whether a particular setpoint is reachable or safe.'],
  ['A plain optimiser lacks the reasoning layer.', 'A differential-evolution search (our DE baseline) needs a predefined decision space and objective for each fault and cannot decide that a sensor should be corrected rather than a gain retuned. In our design the agent chooses the mode and the decision space, and the optimiser becomes one of its tools.'],
  ['Human oversight is part of the loop.', 'Shutdowns and large derates are high-impact decisions that need operator approval, and the agent must explain them through its trace.'],
];

module.exports.DEV_OBJ = [
  'Multi-zone thermal digital twin with fault injection, parameter mismatch and sensor noise (completed in Phase 1).',
  'Re-implementation of the base-paper workflow and four comparison baselines (completed in Phase 1).',
  'Adaptive EKF calibration and ensemble, chance-constrained validation (G1).',
  'Counterexample feedback, feasible-bound tool and LLM-seeded numeric repair (G2).',
  'Diagnosis agent with residual and hypothesis-replay tools (G3).',
  'Operator dashboard with approval and override, and an optional run on a physical TCLab board.',
];

module.exports.SUCCESS = [
  ['G1', 'At 30% plant–model mismatch, the validated-but-failed rate is at most 5%, and plant success is at least 15 percentage points higher than the base workflow with a nominal twin, with no more than twice its decision time.'],
  ['G2', 'With gpt-oss-20b, the recovery rate (successful episodes among those needing a reprompt) is at least 80%, and the mean number of reprompts falls by at least 40% relative to the base workflow.'],
  ['G3', 'Top-1 localisation accuracy of at least 85%, and end-to-end plant success without the oracle within 10 percentage points of the base workflow with the oracle.'],
];

module.exports.DATA = [
  'The environment is confirmed and already implemented. It is a lumped-parameter model of the TCLab temperature control laboratory [16], a widely used benchmark built around an Arduino board with two transistor heaters and thermistors. Each zone is a small thermal mass heated electrically and cooled by convection and radiation, with heat exchanged between neighbouring zones and a first-order sensor lag; equations are integrated with a fourth-order Runge–Kutta step at 1 Hz. With the published parameters, the model reproduces the real board\'s behaviour (zones settle near 71 °C and 62 °C at full power). We use two plants: the two-zone TCLab board and a four-zone chain representing a multi-zone furnace.',
  'Realism is introduced in three ways. The true plant differs from the nominal model by a random multiplicative mismatch of 0, 10, 20 or 30% on heat-transfer coefficients, heater gains, sensor lags and thermal mass. Measurements carry Gaussian noise (σ = 0.15 °C) and 0.01 °C quantisation. Five fault types are injected at a random time between 25 and 30 minutes into each 70-minute episode:',
];
module.exports.FAULTS = [
  ['Heater degradation', 'Actuator', 'Heater gain × 0.30–0.50 on one zone', 'Setpoint becomes unreachable'],
  ['Enclosure heat loss', 'Process', 'Heat-transfer coefficient × 2.5–3.5 on all zones', 'Setpoints unreachable on all zones'],
  ['Local insulation loss', 'Process', 'Heat-transfer coefficient × 3–5 on one zone', 'One setpoint unreachable'],
  ['Sensor bias', 'Sensor', 'Reading offset −7 to −14 °C on one zone', 'Loop overheats the true temperature'],
  ['Stuck-high heater', 'Actuator', 'Heater output frozen at 85–100%', 'Zone may exceed the 60 °C limit'],
];
module.exports.DATA2 = [
  'The Phase-1 evaluation suite contains 120 scenarios: five faults × two plant sizes × four mismatch levels × three seeds. Because free-tier LLM quotas are limited (8,000 tokens per minute and 200,000 tokens per day per model), LLM methods are run on a fixed two-zone subset; Phase 1 reports its 10-scenario core set, which covers all five faults at 0% and 20% mismatch. In Phase 2 the suite grows to five seeds, two noise levels and a held-out set with unseen magnitudes and compound faults. LLMs are accessed through Groq\'s OpenAI-compatible API: openai/gpt-oss-20b as the small model and openai/gpt-oss-120b as the large one, both with low reasoning effort. Every number in this report can be regenerated from the repository.',
];

module.exports.ARCH = [
  ['Models', 'Three LLM agents (diagnosis, planning, action) served through an OpenAI-compatible client with a token-budget pacer, retries and token accounting; the deterministic monitor, validator, fallback and PI loops are ordinary code.'],
  ['Tools', 'snapshot (current measurements, setpoints, outputs, residuals, short trend); retrieve (knowledge subgraph); twin.rollout and validate (simulate a candidate action and check it); in Phase 2 also ekf.estimate, feasible_bounds, test_hypothesis and repair.'],
  ['State and contracts', 'All agent inputs and outputs are typed Pydantic contracts: Snapshot, FaultReport, PlanDecision, RecoveryAction, ValidationResult, LLMCallRecord and DecisionTrace. LLM output that does not parse into a contract counts as a failed proposal and is never executed.'],
  ['Knowledge', 'A typed plant knowledge graph holding structure (zones, heaters, sensors, neighbours), dynamics, the operating-mode state machine (NORMAL, RETUNE, DERATE, SENSOR_CORRECTION, COMPENSATE, SAFE_SHUTDOWN), admissible modes per fault class and constraints. Retrieval returns the subgraph for the implicated zone and its neighbours, a lightweight equivalent of the base paper\'s ontology and Graph RAG.'],
  ['Memory', 'Per-decision conversation and validation history in the trace; no long-term memory is needed for this task.'],
  ['Orchestration', 'An explicit state machine: diagnose, retrieve, plan, act, (repair), validate, then apply, reprompt the responsible agent, or fall back once the budget of five reprompts is exhausted.'],
  ['Human controls', 'Operator approval for shutdowns and large derates, manual override, and the full decision trace for audit.'],
  ['External environment', 'The simulated plant (true parameters hidden from all agents), or a real TCLab board through the same interface.'],
];

module.exports.DIAGRAM_TEXT = 'Figure 2 shows the complete system. Blue components form the base-paper workflow that serves as our main baseline; orange components are the three gap-specific additions, marked G1–G3; grey boxes are deterministic modules. The baseline path runs from the monitor through oracle localisation, knowledge retrieval, the planning and action agents and a matched or nominal twin to the validator, with reprompting and fallback. The proposed path replaces the oracle with the diagnosis agent (G3), adds numeric repair after the action agent (G2), and validates on an EKF-calibrated twin ensemble fed by plant measurements (G1).';

module.exports.BASELINES = [
  ['B0 No recovery', 'The PI loops continue unchanged after the fault (fault-agnostic control).'],
  ['B1 Rule table', 'A fixed fault-type-to-action table with nominal fault magnitudes, applied without simulation (deterministic workflow).'],
  ['B2 Single LLM call', 'One LLM call proposes the mode and parameters; the action is applied without simulation or validation.'],
  ['B3 DE retune', 'Differential evolution [17] searches setpoint derate, PI gains and sensor offset on the nominal twin (non-LLM optimiser, the seed\'s DE line).'],
  ['B4 Base workflow', 'Re-implementation of [1] with a matched twin (its own evaluation assumption, an upper bound) and with a nominal twin (realistic deployment).'],
];

module.exports.RQ = [
  ['G1', 'Under 10–30% plant–model mismatch, does validating on an EKF-calibrated twin ensemble reduce the rate of actions that pass validation but fail on the true plant, compared with the base workflow\'s nominal twin?', 'At 30% mismatch the validated-but-failed rate drops to 5% or less and plant success rises by at least 15 points, with at most twice the decision time.'],
  ['G2', 'Does returning quantitative counterexamples and feasible bounds, together with LLM-seeded numeric repair, raise the recovery rate of a small free-tier LLM?', 'For gpt-oss-20b the recovery rate reaches at least 80% and the mean number of reprompts falls by at least 40%.'],
  ['G3', 'Can a tool-grounded diagnosis agent replace oracle localisation without losing end-to-end safety?', 'Top-1 localisation accuracy is at least 85%, and plant success without the oracle is within 10 points of the base workflow with the oracle.'],
];

module.exports.EVAL = [
  ['Evaluation sets', 'Phase-1 suite (120 scenarios) and the 10-scenario LLM core set (20-scenario subset in Phase 2); Phase-2 extended suite (about 200 scenarios plus a held-out set of unseen magnitudes and compound faults). Each LLM configuration is repeated three times at temperature 0.2.'],
  ['Primary metrics', 'Plant success (no safety violation after the action and healthy zones regulated within ±1.5 °C, with shutdown only when unavoidable); agent success (the base paper\'s definition: a validated LLM action applied without fallback); validated-but-failed rate; safety-violation rate (more than 0.5 °C or 60 s above the 60 °C limit after the action).'],
  ['Secondary metrics', 'Peak temperature, time above the limit, setpoint retention, integrated absolute error, recovery rate, reprompts, fallback rate, localisation accuracy (G3) and EKF parameter error (G1).'],
  ['System measures', 'LLM calls, input and output tokens, LLM latency and total decision time per episode.'],
  ['Comparisons', 'All baselines and the proposed system on identical scenarios, broken down by fault type, plant size and mismatch level; paired tests (McNemar for success rates, Wilcoxon for continuous metrics) with 95% confidence intervals.'],
  ['Ablations', 'G1: nominal twin vs EKF point estimate vs EKF ensemble. G2: pass/fail text vs quantitative violations vs feasible bounds vs numeric repair. G3: oracle vs symptoms only vs residual tools vs counter-hypothesis check. Model size: gpt-oss-20b vs gpt-oss-120b.'],
];

module.exports.MILESTONES = [
  ['Phase 1 (done)', 'Environment, fault library, PI loops, contracts, knowledge graph, twin and validator, LLM client, base workflow, four baselines, evaluation suite, initial results.'],
  ['Phase 2, days 1–3', 'Adaptive EKF, calibrated twin and ensemble validation (G1); first G1 experiment.'],
  ['Phase 2, days 4–6', 'Counterexample feedback, feasible-bound tool, numeric repair (G2); G2 experiment.'],
  ['Phase 2, days 7–9', 'Diagnosis agent and its tools (G3); G3 experiment.'],
  ['Phase 2, days 10–12', 'Full runs, repeats, ablations, statistics, failure analysis.'],
  ['Phase 2, days 13–15', 'Dashboard, optional TCLab hardware run, conference paper and Turnitin reports.'],
  ['Phase 3 (1 week)', 'Slides, live demonstration, viva preparation.'],
];
module.exports.RISKS = [
  ['Free-tier LLM limits (8k tokens/min and 200k tokens/day per model)', 'Token-budget pacer and clean stop/resume at the daily cap (implemented); run the two models in parallel on separate quotas; spread long runs over several days; LLM experiments on the two-zone subset; local open model through Ollama as a last resort.'],
  ['LLM non-determinism', 'Three repeats per configuration, fixed temperature, logged prompts and replies, confidence intervals.'],
  ['EKF divergence under large mismatch', 'Recursive least squares or a batch grey-box fit over a sliding window as a fallback estimator.'],
  ['Compute cost of DE (30–130 s per decision)', 'Smaller population and horizon, vectorised rollouts, parallel scenario shards (already used).'],
  ['No physical testbed', 'Model built on the published TCLab parameters; an optional real board (about USD 35) for a final demonstration.'],
  ['Gemini access blocked for our project', 'Not required; Groq models cover the small/large comparison.'],
];

module.exports.WORK = [
  ['Fatima Khursheed (23I-0746), group head', 'Phase 1: thermal plant and fault library, baselines, scenario suites and evaluation runner, latency and oracle fixes, results report. Phase 2: adaptive EKF and ensemble validation (G1), diagnosis tools (G3), statistics.'],
  ['Saleha Muhammad (23I-0727)', 'Phase 1: agent contracts, knowledge graph, twin and validator interface, LLM client and base-paper agent workflow, Groq integration and LLM runs, tests and documentation, trace viewer. Phase 2: counterexample feedback and numeric repair (G2), diagnosis-agent reasoning (G3), dashboard.'],
  ['Both members', 'Literature review, failure analysis, paper writing and presentation. Both members are responsible for understanding the complete system.'],
];

module.exports.PUBLICATION = [
  'The most publishable contribution is a measurement and a fix. The measurement is the first quantification of the validation–reality gap of LLM fault-tolerant control agents: how often a twin-validated action fails on the real plant when the twin is not a perfect copy. The fix is a calibrated, uncertainty-aware validator that closes this gap. Supporting contributions are evidence that structured physical feedback and numeric repair make small open models viable, and an open multi-zone TCLab fault-tolerant control benchmark. Suitable venues include IFAC symposia (DYCOPS, ADCHEM), IEEE CCTA, and the journals Computers & Chemical Engineering and Journal of Process Control, where the base paper and related work appeared.',
];
