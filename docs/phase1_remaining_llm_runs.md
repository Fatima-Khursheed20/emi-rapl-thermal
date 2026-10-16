# Remaining Phase-1 LLM runs (owner: Saleha)

**Status (16 Oct 2026):** 15 valid real-LLM episodes on the 2-zone LLM subset, all heater-degradation scenarios
(gpt-oss-20b: 5, gpt-oss-120b: 10). Both runs stopped at Groq's free-tier cap of **200,000 tokens per day per model**.
The cap is a rolling 24-hour window, so quota frees up gradually about a day after it was used.

**Goal:** finish `configs/suites/phase1_llm_subset.json`: 20 scenarios × 3 methods = 60 episodes per model.
One base-workflow episode costs about 12–17k tokens, so each model can do roughly 12–15 episodes a day.
Expect **3–4 days** with both models running in parallel.

## How to resume (safe to run any time)

```bash
cd emi-rapl-thermal
# .env must contain GROQ_API_KEY (never commit .env)
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_subset.json --provider groq --model openai/gpt-oss-20b  --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss20b
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_subset.json --provider groq --model openai/gpt-oss-120b --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss120b
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
