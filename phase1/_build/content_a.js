// Deliverable A content: references, base paper, summaries, comparison table, gaps.
module.exports.REFS = [
  // [1]-[12] reviewed papers (base paper = [1])
  'J. Vyas, M. S. Gill, A. Markaj, F. Gehlhoff, and M. Mercangöz, "From detection to action: Using LLM agents for fault-tolerant control," *Journal of Process Control*, vol. 167, Art. no. 103855, Nov. 2026, doi: 10.1016/j.jprocont.2026.103855.',
  'J. Vyas and M. Mercangöz, "Autonomous industrial control using an agentic framework with large language models," *IFAC-PapersOnLine*, vol. 59, no. 6, pp. 349–354, 2025, doi: 10.1016/j.ifacol.2025.07.170.',
  'Y. Wang, J. Vyas, T. Liu, and M. Mercangöz, "Closed-loop control with rule-aligned small language models and multi-agent self-correction," in *Proc. IEEE Conf. Control Technology and Applications (CCTA)*, Aug. 2026, pp. 52–57, doi: 10.1109/CCTA62090.2026.11684321.',
  'T. M. Arif and M. A. Rahim, "Agentic AI for real-time adaptive PID control of a servo motor," *Actuators*, vol. 14, no. 9, Art. no. 459, Sep. 2025, doi: 10.3390/act14090459.',
  'N. S. M. Amin, Y.-W. Kim, and Y.-C. Byun, "Prompt-based PID tuning for adaptive AGV control via few-shot and MultiSpeed strategies," *IEEE Access*, vol. 13, pp. 190685–190700, 2025, doi: 10.1109/ACCESS.2025.3627967.',
  'C. Ren, S.-M. Hong, and R. Tang, "AgentiControl-MPC: Automated model predictive control for buildings using large language model-based multi-agent system," *Advanced Engineering Informatics*, vol. 76, Art. no. 105062, Nov. 2026, doi: 10.1016/j.aei.2026.105062.',
  'W. Xin, W. Liang, and A. Chong, "Causality-constrained hierarchical LLM agents for online rule adaptation in building HVAC control," *Applied Energy*, vol. 427, Art. no. 129012, Jan. 2027 (available online Oct. 2026), doi: 10.1016/j.apenergy.2026.129012.',
  'Z. Zhou *et al.*, "LLM-guided adaptive compensator: Bringing adaptivity to robotic feedback control with large language model," *IEEE Transactions on Automation Science and Engineering*, vol. 23, pp. 10762–10774, 2026, doi: 10.1109/TASE.2026.3700674.',
  'C. Carr, M. Martínez-García, B. J. Marshall, M. Coombes, and Y. Zhang, "Automated UAV controller synthesis via LLM-generated control logic and particle swarm optimization," *IEEE Transactions on Industrial Informatics*, vol. 22, no. 7, pp. 6187–6197, Jul. 2026, doi: 10.1109/TII.2026.3675738.',
  'D. Schall, "Safe integration of large language models into industrial process control: A multi-agent architecture with P&ID-grounded validation," *Autonomous Intelligent Systems*, vol. 6, no. 1, Art. no. 14, Jun. 2026, doi: 10.1007/s43684-026-00136-1.',
  'B. A. Galitsky and A. Rybalov, "Neuro-symbolic verification for preventing LLM hallucinations in process control," *Processes*, vol. 14, no. 2, Art. no. 322, Jan. 2026, doi: 10.3390/pr14020322.',
  'J. Li, S. Li, C. Martin, Z. Chen, D. Chen, and W. Li, "An LLM-assisted multi-agent control framework for roll-to-roll manufacturing systems," *Journal of Manufacturing Systems*, vol. 86, pp. 569–578, Jun. 2026, doi: 10.1016/j.jmsy.2026.04.005.',
  // [13]+ foundational / supporting (not counted toward the ten)
  'S. Yao, J. Zhao, D. Yu, N. Du, I. Shafran, K. Narasimhan, and Y. Cao, "ReAct: Synergizing reasoning and acting in language models," in *Proc. Int. Conf. Learning Representations (ICLR)*, 2023.',
  'X. Guo, D. Keivan, U. Syed, L. Qin, H. Zhang, G. Dullerud, P. Seiler, and B. Hu, "ControlAgent: Automating control system design via novel integration of LLM agents and domain expertise," arXiv:2410.19811, 2024.',
  'J. Vyas and M. Mercangöz, "Autonomous control leveraging LLMs: An agentic framework for next-generation industrial automation," arXiv:2507.07115, 2025.',
  'J. Park, R. A. Martin, J. D. Kelly, and J. D. Hedengren, "Benchmark temperature microcontroller for process dynamics and control," *Computers & Chemical Engineering*, vol. 135, Art. no. 106736, Apr. 2020, doi: 10.1016/j.compchemeng.2020.106736.',
  'R. Storn and K. Price, "Differential evolution—A simple and efficient heuristic for global optimization over continuous spaces," *Journal of Global Optimization*, vol. 11, no. 4, pp. 341–359, 1997.',
  'AISL, Imperial College London, "ctrl-alt-recover: Code for LLM agents for fault-tolerant control," GitHub repository, 2026. [Online]. Available: https://github.com/AISL-at-Imperial-College-London/ctrl-alt-recover',
  'SCImago, "Journal of Process Control," *SJR — SCImago Journal & Country Rank*, 2025. [Online]. Available: https://www.scimagojr.com/journalsearch.php?q=14414&tip=sid',
];

module.exports.SELECTION = [
  'We searched OpenAlex, Crossref, IEEE Xplore, ScienceDirect and arXiv for 2025–2026 work that combines large language model (LLM) agents with feedback control, process supervision or physics-based verification, using queries such as "LLM agent fault-tolerant control", "LLM PID tuning", "LLM model predictive control" and "LLM process control safety". Of roughly sixty candidates we kept twelve peer-reviewed articles that (i) describe a concrete method or agent architecture, (ii) evaluate it on a named plant, benchmark or hardware platform, and (iii) report quantitative results. Preprints and surveys were excluded from the count; well-known preprints such as ControlAgent [14] are cited only as background. Every bibliographic record was checked against Crossref.',
  'The twelve papers fall into four groups: LLM agents that supervise or tune controllers online [1]–[5]; LLM agents that design controllers offline [6], [8], [9], [12]; LLM agents with causal or structural safety layers [7], [10]; and verification of LLM fault reasoning [11]. Ten appear in Elsevier, IEEE, Springer Nature or MDPI journals, one in IFAC-PapersOnLine and one in the IEEE CCTA proceedings.',
];

module.exports.BASE = {
  why: [
    'It addresses the same problem as our project: turning a detected fault into a safe, validated control action using LLM agents grounded in plant knowledge and a digital twin. This is the EMI-RAPL idea of agents that reason while physics models enforce feasibility.',
    'It is directly usable as a comparison point. The agent roles, validation-and-reprompt loop, reprompt budget, deterministic fallback and metrics (success rate, recovery rate, latency, token cost) are clearly specified, and the code is released under an MIT licence [18].',
    'The same group earlier evaluated LLM control agents on the TCLab thermal board [2], [3], [15], the testbed our environment is built on, so re-implementing the workflow on a thermal plant follows the authors\' own line of work.',
    'Its limitations section names the problems we target: the matched-model assumption, oracle fault localisation, and systematic errors that reprompting cannot fix. Our gaps are therefore grounded in the base paper itself.',
  ],
  problem: 'When a fault is detected in a process plant, operators must choose a recovery path and concrete control actions quickly, often during an alarm flood. The paper asks whether LLM agents, grounded in structured plant knowledge and checked by simulation, can take this "detection-to-action" step reliably and within the time the process allows.',
  method: 'The framework decomposes operator work into a multi-agent workflow. A Monitoring Agent raises an intervention once a fault is reported. A Planning Agent retrieves a fault-relevant subgraph from a CPSMod-based ontology through Graph RAG (stored in GraphDB and queried with SPARQL) and selects a minimal-risk recovery path through the plant\'s state machine. An Action Agent turns that path into discrete actuator commands or continuous setpoint changes. A Simulation Agent executes the candidate on a Digital Process Plant Twin, and a deterministic validator checks interlocks, operating envelopes and dynamic feasibility. If the check fails, structured feedback is sent back through a reprompting loop (limit of five); if no acceptable plan appears in time, a deterministic fallback policy takes control. GPT-4o-mini and GPT-4.1-mini are used.',
  data: 'Two simulated benchmarks: a discrete batch mixing module with six fault scenarios (for example pump failure, pump degradation, clogging, sensor fault and leak), and a continuous stirred-tank reactor under PID regulation with three faults (fouling, pump degradation and a cooling valve stuck near closed). Each scenario is run ten times per model.',
  results: 'On the mixing module GPT-4.1-mini succeeded in all 60 runs without needing a reprompt, while GPT-4o-mini succeeded in 51 (85%); its failures concentrated in pump degradation (50% success, 44% recovery rate) and sensor faults (60% success, 33% recovery), with action precision falling to 61.4% because of unnecessary actuations. On the CSTR, GPT-4.1-mini reached 93.3% (28/30) and GPT-4o-mini 76.7% (23/30); under the stuck cooling valve GPT-4o-mini succeeded in only 4 of 10 runs and none of its reprompted runs recovered. Agent calls took about 2–3 s and complete runs 33–52 s, with roughly 13–15 thousand input tokens per CSTR action call.',
  limAuthors: [
    'Matched-model assumption: the twin used for validation is identical to the model that generates the plant behaviour and contains the same injected fault, so robustness to plant–model mismatch, sensor noise and actuator degradation is not evaluated. The authors suggest uncertainty-aware validation, online calibration or interval bounds as future work.',
    'Fault localisation is out of scope and assumed to come from the monitoring layer; without it the agents may keep proposing plausible but inapplicable actions.',
    'Reprompting corrects transient mistakes but not systematic reasoning errors, as the low recovery rates show.',
    'Novel faults cannot be validated because the twin only contains faults modelled in advance; knowledge-graph construction is laborious; latencies rule out hard real-time loops.',
  ],
  limOurs: [
    'Because the validator twin is the plant, a "validated" action is counted as a success. The metric cannot reveal actions that pass validation but would fail on a real plant, which is exactly the risk that matters for deployment.',
    'Only two closely related models from one vendor are tested; there are no open-weight or smaller models and no non-LLM baselines such as a rule table or an optimiser, so the value added by LLM reasoning is not isolated.',
    'Ten runs per scenario with fixed fault magnitudes and no confidence intervals give limited statistical evidence.',
    'Validator feedback says which constraint failed but not by how much or what would be feasible, which may explain why weaker models repeat the same mistake until the budget runs out.',
  ],
  beyond: 'We re-implement the workflow (same agent roles, reprompt budget of five, deterministic fallback and metrics) on a multi-zone thermal plant built from the TCLab energy balance [16]. We evaluate it in two settings: the paper\'s own matched twin, and a realistic nominal twin that knows only the reported fault type. The difference between the two quantifies Gap 1. We then go beyond the paper with three components, one per gap: an online physics-calibrated, uncertainty-aware twin (G1), quantitative counterexample feedback with LLM-seeded numeric repair (G2), and a tool-grounded diagnosis agent that replaces the oracle localisation (G3). Unlike the paper, all success metrics are computed on the hidden true plant and include non-LLM baselines.',
};

// Critical summaries: [title-short, {problem, method, data, results, limitations, relevance}]
module.exports.SUMMARIES = [
  ['[1] Vyas et al., "From detection to action" (base paper)', {
    problem: 'Moving from a raised alarm to a safe corrective action quickly, when operators are overloaded and LLM suggestions are rarely checked against plant physics before they are applied.',
    method: 'Monitoring, planning, action-synthesis, simulation, validation and reprompting agents, grounded in a CPSMod ontology through Graph RAG; every proposal is simulated on a digital twin and checked against interlocks, envelopes and dynamic feasibility, with a fixed fallback after five failed revisions.',
    data: 'Simulated mixing module (six faults) and PID-regulated CSTR (three faults), ten runs each with GPT-4o-mini and GPT-4.1-mini.',
    results: 'GPT-4.1-mini: 60/60 and 28/30 successes; GPT-4o-mini: 85% and 76.7%, with recovery rates of 0–44% in its hardest scenarios; 2–3 s per call and 33–52 s per run.',
    limitations: 'The validation twin is the data-generating model itself, including the injected fault, so mismatch and noise are never tested; localisation is supplied by an oracle; only two related models and no non-LLM baselines are compared. Counting a validated action as success hides validated actions that would fail on a real plant.',
    relevance: 'This is our base paper. We re-implement its workflow on a thermal plant and address the three weaknesses above (Section A.2).',
  }],
  ['[2] Vyas and Mercangöz, IFAC-PapersOnLine 2025', {
    problem: 'Whether LLM agents can run a physical control loop on their own and correct their own mistakes without a human.',
    method: 'Three CrewAI agents: an operator proposes heater actions, a validator checks whether the action keeps the temperature in band, and a reprompter asks for a revision when the check fails; a safety override acts after a fixed number of attempts.',
    data: 'A real TCLab Arduino board controlled for 40 minutes with on/off heating between 25 and 27 °C, using GPT-3.5, GPT-4o-mini, GPT-4o and GPT-4.',
    results: 'Reprompting raised GPT-3.5 from 60.0% to 85.3% valid actions and GPT-4o-mini from 72.5% to 90.0%; GPT-4o was almost always right first time (99.6%). Accuracy did not equal control quality: GPT-4o-mini stayed closest to the band centre, while GPT-4, the slowest model, spent the longest outside the band because its decisions arrived late.',
    limitations: 'The authors point out that inference latency restricts the method to slow processes and that the task is simple. We add that the validator is a threshold rule rather than a physical model, each model was run only once, and on/off switching says little about continuous decisions such as gain or setpoint changes.',
    relevance: 'It uses the same TCLab hardware as our environment and shows both the benefit and the ceiling of plain reprompting (Gap 2) and the absence of a physics-based check (Gap 1).',
  }],
  ['[3] Wang et al., IEEE CCTA 2026', {
    problem: 'Large cloud LLMs are slow, opaque or data-sensitive for edge control; can a compact model produce valid actions when paired with a validator?',
    method: 'A Qwen2.5-1.5B model aligned to control rules with Group Relative Policy Optimisation, placed in an action, validator and reprompter loop with a symbolic, twin-style validator.',
    data: 'Randomised thermal-control simulations: 30 experiments of 500 steps each.',
    results: 'Mean action-alignment accuracy of 91.5% (86.3–100% across cases) at 3.84 s mean latency, and a 95% in-range rate when the symbol mapping was altered.',
    limitations: 'Simulation only, with a symbolic rather than calibrated dynamic validator. The main metric is agreement with a reference action rather than plant safety or tracking, and the small model works only after task-specific reinforcement-learning fine-tuning, which limits transfer to other plants or off-the-shelf models.',
    relevance: 'It shows small models need more than reprompting to be reliable. Our Gap 2 targets the same weakness without fine-tuning, through quantitative physical feedback and numeric repair.',
  }],
  ['[4] Arif and Rahim, Actuators 2025', {
    problem: 'Whether an LLM can tune the PID gains of a physical servo while it runs.',
    method: 'Two agents in an n8n workflow: a control agent (o3-mini) watches steady-state error, overshoot, rise time and settling time and decides when to tune; an optimiser agent (GPT-4.1-mini) proposes new gains from a guided prompt or freely within a fixed safe range, sent to the hardware through a Python/Flask link.',
    data: 'A Quanser QUBE-Servo 2 motor.',
    results: 'Both modes reduced IAE, ISE, MAE and RMSE after the initial transient, but not ITAE or ITSE because of high-frequency oscillation and noise; without the guiding prompt the agent failed to settle on final gains in about one run in ten.',
    limitations: 'Only three runs are tabulated and the detailed analysis uses one, without statistics. Safety rests on a static gain box, so a destabilising gain set inside the box would still be applied. There is no comparison with classical tuning on an equal budget and no fault scenario.',
    relevance: 'A hardware example of agentic tuning without pre-execution verification, which motivates the twin-based validator our work keeps and strengthens.',
  }],
  ['[5] Amin et al., IEEE Access 2025', {
    problem: 'PID tuning for warehouse AGVs is laborious and usually needs system identification or repeated experiments.',
    method: 'Prompt-only gain inference through in-context learning: MultiSpeed prompting interpolates gains from the target speed, and Few-Shot + MultiSpeed adds worked examples.',
    data: 'A two-wheeled AGV at five speeds between 5 and 25 m/min.',
    results: 'Gains stayed close to simulation-optimised values, kept physically sensible trends (Kp rising and Ki falling with speed), held tracking RMSE within 5–10% of optimal and cut calibration effort by over 80%.',
    limitations: 'A single LLM call with no feedback loop or safety check; accuracy relies on exemplars from an existing optimiser, so it is unlikely to cope with dynamics unlike those examples, for instance after a fault. Only one vehicle under nominal conditions is tested.',
    relevance: 'It represents the single-call, non-agentic design used as our baseline B2, which we argue is insufficient once the plant changes in ways the prompt has not seen.',
  }],
  ['[6] Ren et al., Advanced Engineering Informatics 2026', {
    problem: 'Developing MPC controllers for buildings needs substantial expertise and time, which blocks wide deployment.',
    method: 'AgentiControl-MPC: six LLM agents share data processing, predictive-model design, MPC formulation, code generation and error correction, coordinated by inter-layer, intra-layer and state-aware communication.',
    data: 'The BESTEST Hydronic Heat Pump case from the BOPTEST simulation framework.',
    results: 'Across repeated runs the multi-agent system produced working controllers 93.3% of the time against 66.7% for a single-agent baseline; the best generated MPC cut energy cost by 52% and thermal discomfort by 69% relative to the baseline PI controller.',
    limitations: 'One simulated building is studied, so generalisation is untested. "Success" means a controller was produced and ran, not that it stays safe under faults or model error, and the task is offline design rather than a time-limited online decision.',
    relevance: 'A clean multi-agent versus single-agent comparison in a thermal domain that supports our agentic justification; like the base paper it trusts its simulator completely (Gap 1).',
  }],
  ['[7] Xin et al., Applied Energy 2026', {
    problem: 'Adaptive multi-zone HVAC control normally needs a building-specific model or a trained RL policy, both costly to transfer between buildings.',
    method: 'Hierarchical LLM agents propose hourly updates to rule-based controllers, which issue 15-minute setpoints. Each update must pass structural checks, checks against a human-confirmed causal graph built during onboarding, and zone cooling allowances.',
    data: 'BOPTEST cases with one, two and five zones, compared with basic and enhanced rule-based control, hierarchical MPC, PPO and multi-agent PPO.',
    results: 'Highest mean reward and lowest energy in all three cases, 2.2–43.2% less energy than the baselines, small comfort deviations (0.019–0.454 PMV·h), and fewer safety interventions with the causal layer active; ablations cover memory, cross-zone coordination and LLM "thinking".',
    limitations: 'The causal graph is built and confirmed by hand. The checks are causal and structural rather than quantitative rollouts, so a correctly directed but wrongly sized update can pass, and no equipment faults are injected.',
    relevance: 'The most thorough evaluation design in our set and a template for our baselines and ablations; its causal checks inspire the counter-hypothesis test in our diagnosis agent (Gap 3).',
  }],
  ['[8] Zhou et al., IEEE T-ASE 2026', {
    problem: 'LLM-designed feedback controllers have mostly been shown on simplified systems, with little comparison to expert designs or real robots.',
    method: 'The LLM designs a compensator that makes an unknown plant respond like a chosen reference model, following the idea of model-reference adaptive control, instead of writing a controller from scratch; a Lyapunov analysis supports stability.',
    data: 'A two-degree-of-freedom soft robot and a one-degree-of-freedom humanoid shoulder, in simulation and on hardware.',
    results: 'Performance comparable to four conventional adaptive controllers, with a simpler reasoning process than an LLM-designed adaptive controller.',
    limitations: 'The authors note that the compensator is only effective within a bounded region of tracking-error conditions, becomes ineffective when its structural assumptions are violated, and that the Lyapunov analysis is carried out on a single system. We add that design happens offline and stability is argued afterwards rather than checked before each deployment; only two low-DoF platforms are studied and faults are not considered.',
    relevance: 'It confirms that dealing with an unknown or mismatched plant is the central difficulty for LLM-designed control, the issue our Gap 1 tackles for supervisory recovery, and represents the robotics strand of EMI-RAPL.',
  }],
  ['[9] Carr et al., IEEE TII 2026', {
    problem: 'LLM-guided program synthesis works on benchmarks but has rarely produced controllers deployed on real robots.',
    method: 'The LLM writes the structure of the control law and particle swarm optimisation tunes its coefficients with a reward from a Markov decision process; candidates move from a custom simulator to PX4 software-in-the-loop and then to a physical UAV.',
    data: 'Lemniscate and Lissajous trajectory tracking, against PID with a disturbance observer and LQR.',
    results: 'The synthesised law tracked better than both baselines, with at least about 38% lower mean squared error in real flights.',
    limitations: 'An offline, optimisation-heavy process suited to design rather than time-limited recovery; one platform and two trajectories are tested and fault robustness is not studied.',
    relevance: 'Its central lesson, that the LLM should decide structure and an optimiser should decide numbers, is the basis of our Gap 2 approach, which applies the same split inside an online recovery loop.',
  }],
  ['[10] Schall, Autonomous Intelligent Systems 2026', {
    problem: 'Hallucination and the lack of physical understanding make direct LLM control in safety-critical processes unacceptable.',
    method: 'The Autonomous Action Execution framework confines the LLM to an observation-only monitor, while deterministic verification and execution agents make every safety-relevant decision. SCADA data, P&IDs and procedures are converted to text, and proposals are checked by traversing the P&ID graph for tag existence, actuatability, fail-state consistency and downstream effects; baselines B0–B3 add components one by one.',
    data: 'Three Tennessee Eastman Process scenarios plus synthetic polymer-reactor and dryer cases.',
    results: 'The validator caught all 43 crafted invalid proposals, and over 50 LLM runs, in which models proposed unsafe actions 10–70% of the time, it caught every invalid proposal in the covered categories.',
    limitations: 'The checks are structural, so a physically wrong setpoint on a valid tag would pass; the scenarios are synthetic, and keeping the LLM out of the action path limits autonomy.',
    relevance: 'It quantifies how often LLMs propose unsafe actions, which supports a validator, while showing that structural checks alone are not enough (Gap 1).',
  }],
  ['[11] Galitsky and Rybalov, Processes 2026', {
    problem: 'LLMs produce fault explanations that sound plausible but contradict physics, sensor evidence or plant dynamics.',
    method: 'The LLM (GPT-5.1) only generates explanations and a symbolic layer judges them: abductive logic programming tests coherence, counter-abduction builds rival hypotheses from mass and energy balances, and a discourse-weighted variant favours the central clauses of operator notes and alarm logs.',
    data: 'A 500-scenario process-control hallucination dataset covering faults such as pump restriction, valve stiction, fouling and runaway, plus a 36-person user study.',
    results: 'Logical accuracy improved by up to 18%; the full discourse-weighted variant raised consistency by 15 and 12 points in the ablation; inference time fell by more than 20%; user trust rose by 23%.',
    limitations: 'The authors acknowledge synthetic or semi-synthetic scenarios and a dependence on a complete process ontology. The work stops at explanation and never closes the loop to a control action.',
    relevance: 'Direct evidence that LLM fault diagnosis must be verified, motivating the tool-grounded diagnosis agent with a counter-hypothesis check in our Gap 3.',
  }],
  ['[12] Li et al., Journal of Manufacturing Systems 2026', {
    problem: 'Setting up and adapting tension and speed controllers on roll-to-roll lines consumes scarce expert time.',
    method: 'A five-phase LLM-assisted multi-agent framework: system identification from operating data, automatic controller selection and tuning, simulation-to-real adaptation with safety checks, continuous monitoring with diagnostics, and periodic model refinement.',
    data: 'A simulated multi-span roll-to-roll web-handling system: the "real" plant is itself a simulation, and the controller is tuned on a deliberately mismatched model (8.3–50% parameter deviations); hardware testing is left to future work.',
    results: 'RMSE fell by 55.7% for tension control and 82.4% for velocity tracking, outperforming an MPC baseline.',
    limitations: 'The authors list hardware validation on a physical roll-to-roll testbed and extension to other manufacturing processes as future work, and note that tension–velocity coupling grows stronger at production speeds than at the low speed they tested. We add that each configuration appears to be evaluated in a single run without repeats or statistics, and that the Monitoring Agent is described but never evaluated: no faults or degradation are injected in the validation study.',
    relevance: 'It shows that refreshing the model online matters in practice, the step our base paper leaves out, and gives a manufacturing example of the EMI-RAPL idea.',
  }],
];

module.exports.TABLE = [
  // #, title, year&venue, data, method, metrics, results, gap
  ['1 ★', 'LLM agents for fault-tolerant control (BASE)', '2026, J. Process Control (Q1)', 'Sim. mixing module + CSTR, 9 faults', 'Monitor–plan–act–simulate–validate–reprompt; Graph RAG; digital twin; fallback', 'Success, recovery rate, plan/action correctness, latency, tokens', 'GPT-4.1-mini 100% / 93%; GPT-4o-mini 85% / 77%; recovery 0–44% on hard faults', 'Matched twin; oracle localisation; reprompting cannot fix systematic errors'],
  ['2', 'Agentic framework for industrial control', '2025, IFAC-PapersOnLine', 'Real TCLab board, 40 min', 'Operator, validator and reprompter agents (CrewAI)', 'Valid-action rate, time outside band', '60→85% (GPT-3.5); 99.6% (GPT-4o)', 'Rule-based validator; single run; latency'],
  ['3', 'SLM control with self-correction', '2026, IEEE CCTA', 'Randomised thermal sims, 30×500 steps', 'GRPO-tuned Qwen2.5-1.5B + validator + reprompter', 'Action alignment, in-range rate, latency', '91.5% alignment, 3.84 s', 'Needs RL fine-tuning; symbolic validator'],
  ['4', 'Agentic real-time PID of a servo', '2025, Actuators', 'Quanser QUBE-Servo 2', 'o3-mini monitor + GPT-4.1-mini optimiser; safe gain box', 'IAE, ISE, MAE, RMSE, ITAE, ITSE', 'IAE/ISE/RMSE reduced; ITAE/ITSE not; ~1/10 unguided runs fail', 'Three runs; no pre-execution check; no classical baseline'],
  ['5', 'Prompt-based PID for AGVs', '2025, IEEE Access', 'Two-wheeled AGV, 5 speeds', 'Single-call few-shot / MultiSpeed prompting', 'RMSE vs optimum, calibration effort', 'Within 5–10% of optimum; >80% less effort', 'Non-agentic; no feedback, faults or safety'],
  ['6', 'AgentiControl-MPC', '2026, Adv. Eng. Informatics', 'BOPTEST heat-pump building', 'Six-agent MPC development pipeline', 'Generation success, energy cost, discomfort', '93.3% vs 66.7% single agent; −52% cost', 'One building; offline; success ≠ safe operation'],
  ['7', 'Causality-constrained HVAC agents', '2026, Applied Energy', 'BOPTEST 1-, 2-, 5-zone', 'Hierarchical LLM agents gated by causal graph', 'Reward, energy, PMV·h, interventions', '2.2–43.2% less energy than baselines', 'Manual causal graph; no quantitative rollout; no faults'],
  ['8', 'LLM-guided adaptive compensator', '2026, IEEE T-ASE', 'Soft robot, humanoid shoulder (sim + real)', 'LLM-designed MRAC-style compensator; Lyapunov analysis', 'Tracking error vs adaptive controllers', 'Comparable to four adaptive controllers', 'Offline design; no online checks or faults'],
  ['9', 'LLM + PSO UAV controller synthesis', '2026, IEEE TII', 'UAV sim → PX4 SITL → real UAV', 'LLM writes control law; PSO tunes coefficients', 'Trajectory MSE', '≥38% lower MSE in real flights', 'Offline and compute-heavy'],
  ['10', 'P&ID-grounded validation', '2026, Auton. Intell. Systems', 'Tennessee Eastman + 2 synthetic plants', 'Observation-only LLM; deterministic graph verifier', 'Recall of invalid proposals, unsafe-proposal rate', '100% recall; LLMs unsafe in 10–70% of runs', 'Structural checks only; no dynamics'],
  ['11', 'Neuro-symbolic hallucination checks', '2026, Processes', '500-scenario dataset + 36-user study', 'GPT-5.1 generator; abductive and counter-abductive verifier', 'Logical accuracy, consistency, trust', '+18% accuracy; +15/+12 consistency; +23% trust', 'Explanations only; synthetic data'],
  ['12', 'LLM multi-agent roll-to-roll control', '2026, J. Manuf. Systems', 'Simulated R2R web-handling system', 'Sys-ID, tuning, sim-to-real safety checks, monitoring, refinement', 'Tension and velocity RMSE', '−55.7% / −82.4% RMSE; beats MPC', 'Simulation only; single runs; monitoring not evaluated'],
];

module.exports.GAPS_INTRO = 'Reading the twelve papers side by side shows a common pattern: almost all of them place a verification step between the LLM and the plant, but that step is either a perfect copy of the simulator [1], [6], a rule or symbolic check [2], [3], [7], [10], or absent [4], [5]. In parallel, the papers that measure repeated revisions [1]–[3] show that the LLM often cannot repair its own proposal from pass/fail feedback, and the papers on diagnosis [10], [11] show that LLM fault explanations cannot be trusted without verification. From these observations we derived six candidate gaps and selected the three that are specific, supported by named papers, tied to the base paper and measurable on our plant within the semester.';

module.exports.CANDIDATES = [
  ['G1 (selected)', 'Validation assumes a twin identical to the plant; mismatch, noise and unknown fault size are untested.', '[1], [2], [3], [6], [10], [12]'],
  ['G2 (selected)', 'Pass/fail reprompting cannot repair systematic numeric or mode errors, especially for small models.', '[1], [2], [3], [9]'],
  ['G3 (selected)', 'Fault localisation is assumed to be given, and LLM fault diagnosis is unverified.', '[1], [7], [10], [11]'],
  ['G4', 'LLM latency (seconds to a minute) versus process dynamics; fast loops are excluded.', '[1], [2], [3]'],
  ['G5', 'Weak statistics: few runs, no confidence intervals, few or no non-LLM baselines.', '[1], [2], [4], [6]'],
  ['G6', 'High manual effort to build plant knowledge graphs and causal graphs.', '[1], [7]'],
];

module.exports.GAP_TABLE = [
  ['G1: Validation trusts a perfect twin. Mismatch, noise and unknown fault magnitude are never tested, so a "validated" action can still fail on the real plant.',
   'Base paper states the matched-model assumption and leaves mismatch and noise untested [1]; validators in [2], [3] are rule or symbolic checks; [10] checks structure only; [6] trusts one simulator; [12] needs online model refinement in practice.',
   'Adaptive extended Kalman filter that jointly estimates zone temperatures, heater gains, heat-loss coefficients and sensor bias with EWMA noise adaptation; the twin uses these estimates, and candidate actions are validated over an ensemble sampled from the EKF covariance (accepted only if the 95th-percentile peak temperature and tracking error meet the limits).',
   'Validated-but-failed rate, plant success and safety-violation rate on the hidden true plant, at 0/10/20/30% parameter mismatch and two noise levels; EKF parameter error; added decision time. Compared with the base workflow using matched and nominal twins.'],
  ['G2: Pass/fail reprompting cannot fix systematic errors. The model keeps repeating a wrong mode or wrong numbers until the budget runs out, especially with small models.',
   'Recovery rates of 0–44% and budget exhaustion for GPT-4o-mini [1]; 15% of actions still wrong after reprompting with GPT-3.5 [2]; a small model needs RL fine-tuning [3]; separating LLM structure from optimiser numbers works [9].',
   'The validator returns quantitative counterexamples and physics-derived feasible bounds (for example the highest reachable temperature of a degraded zone from the calibrated energy balance), routes mode errors back to the planner, and runs a bounded differential-evolution repair seeded with the LLM proposal inside the chosen mode.',
   'Recovery rate, mean reprompts, fallback rate and plant success for gpt-oss-20b and gpt-oss-120b; tokens and wall time; ablation of each feedback element.'],
  ['G3: Fault localisation is assumed and LLM diagnosis is unverified, so the base workflow cannot run when the monitor reports only symptoms.',
   'Localisation declared out of scope, with failures when it is missing [1]; LLM fault explanations hallucinate [11]; LLM confined to observation because of hallucination [10]; causal constraints stabilise LLM decisions [7].',
   'A diagnosis agent that calls physics-residual tools (EKF parameter deviations, innovation tests, replay of recent data under each candidate fault on the twin) and must pass a counter-hypothesis check before committing to a ranked fault report.',
   'Top-1 localisation accuracy (fault kind and zone); end-to-end plant success without the oracle, compared with the base workflow with and without the oracle; unsafe actions caused by misdiagnosis.'],
];
