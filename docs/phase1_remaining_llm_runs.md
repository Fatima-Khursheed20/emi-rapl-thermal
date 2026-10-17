# Remaining Phase-1 LLM runs (owner: Saleha)

**Status (17 Oct 2026):** the 10-scenario **core set** reported in the Phase-1 PDF (`configs/suites/phase1_llm_core.json`,
all five faults at 0 % and 20 % mismatch) is done: 63 valid episodes in total, with gpt-oss-120b complete and
gpt-oss-20b missing only `actuator_stuck_high-mm00-s0`. Groq's free tier caps each model at **200,000 tokens per day**,
on a rolling 24-hour window.

**Optional next step (Phase 2):** the seed-1 half of `configs/suites/phase1_llm_subset.json` (10 more scenarios ×
3 methods per model). One scenario costs about 30k tokens across the three methods, so expect roughly **2 days** with
both models running in parallel. Replace `phase1_llm_core.json` with `phase1_llm_subset.json` in the commands below.

## How to resume (safe to run any time)

```bash
cd emi-rapl-thermal
# .env must contain GROQ_API_KEY (never commit .env)
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_core.json --provider groq --model openai/gpt-oss-20b  --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss20b
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_core.json --provider groq --model openai/gpt-oss-120b --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss120b
```

- Each run **resumes** where it stopped: finished `(scenario, method)` pairs in `summary.csv` are skipped.
- When the daily cap is hit, the run prints `STOPPED: ... daily quota reached` and exits **without recording the unfinished
  episode**. Run the same command again the next day.
- Run the two commands in two terminals, because each model has its own quota.
- Check progress: `.venv/Scripts/python scripts/show_trace.py --run phase1_llm_gptoss20b --list`

## When the runs are complete

```bash
.venv/Scripts/python scripts/make_report.py --out docs/results     # rebuild tables + figures
git add results/phase1_llm_gptoss20b results/phase1_llm_gptoss120b docs/results
git commit -m "Complete Phase-1 LLM baseline runs on the 20-scenario subset"
git push
```

Then ask for the Phase-1 document's results section (B.16, Tables 13–14, Figures 3–4) to be regenerated from the new
numbers.

## Faster options (optional)

- A new Google AI Studio key in `.env` as `GEMINI_API_KEY` (`--provider gemini`) adds a third model with its own free
  quota. The current Google project is blocked (HTTP 403), so the key must come from a **new** project.
- Shorter prompts would cut tokens per call by ~30–40% (compact JSON in `llm/prompts.py`), but only change this for
  the Phase-2 runs. Mixing prompt versions inside one Phase-1 run would make the episodes incomparable.
