# Development log

## 2026-11-09

| Observation | Change | Measured effect |
|---|---|---|
| Phase 1 documented five repeated rejections of a sensor-offset proposal in `p1-z2-sensor_bias-mm20-s1`. The nominal twin assumed a larger bias than the one injected. | Added measurement-based fault replay, adaptive EKF state and parameter estimates, and validation across a covariance ensemble. | The screening run reports the full and no-G1 configurations on identical scenarios. See `results/phase2_screen_e4/gap_analysis.json`. A scripted run cannot establish the live-model effect. |
| Phase 1 documented a degraded heater stuck in RETUNE because the setpoint was unreachable. | Added feasible temperature bounds, replanning feedback on unreachable RETUNE, and bounded DE within supported numeric modes. | A deliberately rejected 0 °C sensor offset was repaired to 8.79 °C on the dev fixture. Predicted tracking error fell from 9.995 °C to 1.205 °C and the candidate passed revalidation. No repair fired in screening. H2 still needs live gpt-oss-20b. |
| The first approval integration test failed during metric serialization. The EKF state in the trace was a JSON list, while the NumPy split used in scoring required an array. | Convert the saved state back to an array when calculating error. | Test suite moved from 17 passed and 1 failed to 18 passed. A manual CLI run with rejection also logged `action_applied: false`. |

## Deliverable A robustness revision

| Observed failure | Change | Measured effect |
|---|---|---|
| A rejected proposal mixing valid zone 0 and nonexistent zone 99 crashed inside numeric repair. | Allow only repairable structural violations to enter numeric optimisation. | The regression exits before simulation and preserves the validator rejection. |
| A pending shutdown could be scored as applied after the episode ended. | Record the physical actuation timestamp, log expired proposals, and score applied actions only. | The delayed-action regression reports no application, agent success, or shutdown. |
| Two stuck heaters overheated after ordinary fallback rejection. | Add a separately checked emergency power cut using simulated hold and cut trajectories. | Both prior failures applied shutdown below the post-action limit. Screening safety violations fell from two to zero. One other shutdown was unnecessary under the oracle criterion. |
| Secondary faults were injected at the primary onset. | Order all injected faults by their configured onset times. | The staggered regression detects the secondary sensor step at its own onset. |

## 2026-11-10 Final evaluation hardening

| Observed failure | Change | Measured effect |
|---|---|---|
| The analysis script accepted a 14-of-140 screening run. Existing checkpoint filenames could also cause a corrupt or mismatched episode to be skipped. | Verify the complete scenario, method and repeat grid, bind runs to their configuration and code, and check saved episode contents. Pause without publishing aggregates. | The resume test rejects the paused run, preserves the first checkpoint, rebuilds a corrupted episode and rejects analysis of a modified CSV. |
| Authentication and transient provider errors could end up in the experiment as agent failures. A reply truncated inside an outer object could also yield a nested action. | Classify provider failures, respect short retry waits, pause on exhausted quota, and validate one complete reply. | Mocked HTTP tests cover authentication, permissions, missing models, daily quota, brief throttling, server errors, connection errors and failed JSON generation. |
| The demo could present a rejected fallback for approval and then apply a different power cut. A proposal at the terminal sample could be scored as actuated. | Show the selected action. Separate selection from actuation and require a simulated sample after actuation. | Regression tests verify the action displayed for approval and confirm no actuation or shutdown at the last sample. |
| The validator counted time over the limit per zone, while the evaluator counted time with any zone over the limit. Mode NORMAL also accepted controller changes. | Share the duration rule, report pre-actuation excursions separately, enforce mode fields, and check the ensemble p95 against the Phase 1 limit. | An 80-second excursion split across two zones now fails both validator and evaluator. NORMAL cannot change heater limits. |
| A live single-call proposal with zero integral time could crash the controller. Healthy traces were forced into a fault hypothesis, and pre-fault alarms could receive the future oracle label. | Bound numerical inputs, include the healthy counter-hypothesis, and gate the oracle on actual onset. | Regression cases cover zero integral time, unsafe structures, missing samples and early alarms. |
| Twin rollout and replay repeatedly stepped equivalent prefixes. | Reuse the simulated healthy prefix and provide optional acceleration of the same numerical kernels. | The rollout parity test checks temperatures, measurements and heater power against the stepwise simulator through a delayed shutdown. The pure Python demo also completes. |

Final checks passed 61 regression tests, regenerated all five fixed splits
byte-for-byte, and exercised process spawning, a fresh wheel install and the
portable demo. The scripted runs finished 4,400 holdout episodes, 220 core
episodes, 140 screening episodes and 18 stress episodes. Their manifests,
tables and traces are saved in `results/phase2_final_*_scripted`. The full
supervisor met the plant-success criterion in 264 of 400 scripted holdout
scenarios and had eight post-action safety violations.

The 660-episode live execution path was exercised with mocked Groq HTTP
responses. A simulated quota pause preserved seven checkpoints, and the
resume verified all 660 rows across three repeats. The mocked results serve
as software verification. The live preflight and benchmark use the group's
own Groq account.

## Follow-up evaluation audit

The diagnosis ablation now keeps the adaptive estimator and repair path,
while receiving only monitor symptoms and skipping replay and diagnosis.
The matched and nominal base-paper workflows remain the oracle comparisons.
The safety table adds a stricter plant-success endpoint covering fault onset
through episode end. The original endpoint remains available for comparison.
The gap analysis now counts repair attempts, validated repairs and episodes
with repair separately.

The revision passed 63 tests and regenerated all 4,778 scripted checkpoints.
The fixed splits match the previous ZIP byte for byte. The rerun preserves
the earlier scripted outcomes for methods other than the changed G3 ablation.
A 66-episode mock-provider test covered all 11 methods, three repeats, and
resume after a simulated quota interruption. Run both Groq models locally
for the live comparisons and provider latency and usage measurements.
