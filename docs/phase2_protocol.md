# Phase 2 evaluation protocol

Project G3-09, EMI-RAPL Thermal. The starting point is upstream commit
`6e708c4dba7bc23f8770eb458680475fbc94ec82`. See the submitted Phase 1 proposal
in `phase1/` for the approved research questions, thresholds and base paper.

## Data and comparators

- Development has 20 single-fault episodes with seed family 10.
- Confirmatory test has 400 single-fault episodes, crossed over five fault types, two
  plant sizes, four mismatch levels, five seed families and two noise levels.
- The locked LLM core contains 20 of those test episodes, balanced by plant size,
  fault and two mismatch/noise conditions. It pairs 0% mismatch with 0.05 °C
  noise and 30% mismatch with 0.15 °C noise. Use the same IDs for both models.
  Compare methods within each condition. Use the fully crossed test split to
  separate mismatch from noise.
- The offline screen contains 20 separate episodes. Its findings describe that
  screening split and the scripted agent only.
- Stress has 18 episodes with out-of-range magnitudes, eight of them with a concurrent
  sensor fault. The replay library fits one fault at a time. For compound episodes,
  localisation measures the primary fault only. Check true-plant outcome and safety
  independently of that score.
- All methods in a comparison use identical scenarios and 30 seconds of simulated
  actuation delay. Evaluation uses hidden plant state. Match results on scenario
  and repetition before making paired comparisons.
- E2 is a local reimplementation of the Vyas et al. workflow on this simulator.
  The original CSTR/mixer numbers are from a different environment. Use the
  matched and nominal implementations as local comparisons. See
  [base_paper_mapping.md](base_paper_mapping.md).

## Metrics and questions

| Experiment | Readout |
|---|---|
| E1 | Plant success and safety for PI-only, fixed rules, deterministic DE and single-call LLM. Scripted single-call is a proxy. |
| E2 | Same readout for matched and nominal base-paper workflow with oracle localisation, and a nominal symptoms-only comparator. |
| E3 | Plant and agent success for the full supervisor, with saved diagnosis, prompts, responses, validation and resulting action. |
| E4 / H1 | At 30% mismatch, compare validated-but-failed, plant success and decision time against the nominal base workflow. The Phase 1 targets are ≤5%, ≥15 percentage points of improvement and ≤2× latency. Report gain and loss scale RMSE and bias RMSE. |
| E4 / H2 | On gpt-oss-20b, check ≥80% recovery among episodes requiring a reprompt and ≥40% reduction in mean reprompts against the nominal base workflow. Inspect repair-tool events separately because a successful first-attempt repair can prevent a reprompt. |
| E4 / H3 | Check ≥85% correct kind and zone and plant success within 10 percentage points of the oracle baseline. Report accuracy over all episodes and conditional on post-onset detection. |
| E5 | Disable calibration, numeric repair and diagnosis separately. With G3 disabled, the agent receives symptoms, retains calibration and repair, and skips fault replay and diagnosis. The E2 baselines provide the separate oracle comparisons. |
| E6 | Compare decision time, API time, retries, tokens, calls, fallbacks, safety and estimated cost of reported tokens. Run with one worker for timing comparisons. |

The validated-but-failed metric counts applied, validated, non-fallback actions
whose plant outcome fails. It uses all episodes as its denominator, as in Phase 1.
Read it alongside agent success and plant success. A method that rejects most actions
can score low on validated-but-failed while performing poorly on the plant.
Agent success counts an applied non-fallback action. For an unvalidated baseline this
is only an application indicator. Plant success and safety are the comparable metrics.
An accepted NORMAL decision holds the current settings. Its logged actuation
does not imply a controller parameter changed.

Post-action safety starts with the first sample generated using the selected
settings. If there is no actuation, it covers the period after fault onset.
The tolerance is a peak at most 60.5 °C and at most 60 seconds with any zone
above 60 °C. The run also records excursions since fault onset and before
actuation. An emergency power cut can reduce risk while leaving a violation.
The trace records mitigation and the safety outcome separately.
The original `plant_success` endpoint uses post-actuation safety.
`plant_success_since_fault` additionally requires the full post-onset window to
stay within the tolerance. Use `safety_outcomes.csv` to report both endpoints.
Failure categories in `failure_counts.csv` use the original endpoint.

Use `analyze_phase2.py` on a verified complete run containing the full and
comparison methods. Its bootstrap keeps faults, noise and mismatch variants,
and repeats together within a plant size and seed family. Its paired tests
use the same scenario/repeat assignments. Bootstrap intervals and Wilcoxon
tests require at least five seed blocks. The 20-scenario LLM core has two
blocks, so its comparisons are descriptive. McNemar's exact test is shown
only where each block contributes one pair. A group with no reprompt episodes
has an undefined recovery rate.
Treat intervals from the small screening split as exploratory. Grouped means and
sample standard deviations in aggregate CSVs are computed over repeats. A scripted
run has one deterministic repeat, so its standard-deviation cells are empty.
For G2, a validated repair means the repaired candidate passed the twin check.
Use plant success to assess the physical outcome. For E6, the cost estimate
covers reported tokens in saved episodes. API calls made before an interruption
can be absent if the episode had to restart. Decision wall time includes pacing
and retries within the recorded decision. The plant advances using the fixed
simulated delay.

## Run and submission checks

1. Confirm any supervisor feedback and document how it was addressed.
2. Generate or verify the fixed suite files before running live evaluations.
3. Run both approved models three times on the same LLM core. The runner does this
   automatically per model. Use the extended split for offline comparisons.
4. Run stress separately. Review the examples in `representative_traces.json` and
   the full checkpoint traces. Check the completion manifest before using a result.
5. Record provider and model availability, pricing if applicable, and any deviations.
   The manifest records the requested settings, split and code hashes, package
   versions and repeat count. The traces record returned model and version
   metadata when supplied. Hosted inference may be nondeterministic. Record
   missing usage alongside any cost estimate.
6. The team writes the original IEEE/ACM paper, generates the two Turnitin reports
   on its final version, and coordinates the release and submission. Use the latest course announcement for the submission and release deadline.

## Interpretation limits

The nominal simulator assumes one localised fault and shares the thermal model family
with the true simulation. The calibrated version estimates effective gain and loss
scales from measured temperatures and commanded power. Constant inputs can make those
scales hard to separate. The five-member ensemble rejects an action if any member
fails the thermal or regulation checks. It also rejects when the empirical p95
peak exceeds 60 °C. The empirical percentile from five samples describes the
screened ensemble.

Scenario seeds are saved with each episode. The covariance ensemble and bounded
repair each use seed 42. The DE baseline uses seed 0. Live repeats reuse the same
plant inputs and differ in the provider's generation.

The monitor can trigger before fault onset, including on high measured temperature
during warm-up. The first trigger is retained for comparisons, and false alarms
are logged. Oracle labels are available only after the primary fault actually
starts. Only the matched baseline sees hidden plant parameters. The proposed system
estimates its twin state from observations. This workflow evaluates a simulator.
