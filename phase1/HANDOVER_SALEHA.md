# Phase 1 handover: Fatima → Saleha

Project **G3-09 EMI-RAPL**, refined to *Mind the Twin Gap: Physics-Calibrated, Uncertainty-Aware LLM Agents for
Fault-Tolerant Multi-Zone Thermal Control*. Handover date: 16 Oct 2026. Phase-1 deadline: see Google Classroom
(about 10 days after the 16 Oct announcement).

**A repo clone is all you need.** Everything is in https://github.com/Fatima-Khursheed20/emi-rapl-thermal: code,
results, decision traces, the submission PDF/Word file, notes, screenshots and the scripts that rebuild the document.
The one thing a clone does not include is an API key: create **your own** free Groq key (see §4). Never share keys over
chat or commit them.

---

## 1. What to submit (Google Classroom → Phase 1 assignment)

| Item | File / value | Status |
|---|---|---|
| One PDF with Deliverable A then Deliverable B | `phase1/Phase1_G3-09_23I-0746.pdf` (22 pages) | ✅ ready |
| GitHub link (Deliverable C), added as a link in the **same** submission | https://github.com/Fatima-Khursheed20/emi-rapl-thermal | ✅ ready |
| File name `Phase1_<ProjectCode>_<GroupHeadRollNo>.pdf` | `Phase1_G3-09_23I-0746.pdf` | ✅ |
| First page: project code, title, names and roll numbers | on the title page | ✅ |
| Supervisor/instructor access to the repo | instructor `Owais-Idrees` invited as collaborator | ⚠ he must accept the invite (it expires 7 days after 16 Oct). If he hasn't, ask Fatima to re-send it from repo **Settings → Collaborators** |

> ⚠ **Who submits.** The guideline says *"Only the group head submits."* The document names **Fatima (23I-0746)** as
> group head, and the filename uses her roll number. Either submit from **Fatima's Classroom account**, or, if you
> submit from yours, first get the instructor's OK and change the group head on the title page (`phase1/_build/build.js`,
> `team` list) and the filename to `Phase1_G3-09_23I-0727.pdf`.

**Before you press submit:**
1. Open the PDF and read it once end to end.
2. Paper [7] (*Applied Energy*) was published online in Oct 2026, but its issue is dated **Jan 2027**. Online-first
   usually counts as 2026; if the supervisor disagrees, swap it for a reserve paper (listed in `phase1/A_literature_notes.md`).
3. If you finished the LLM runs (§3), rebuild the document first (§5). Otherwise submit as is: the LLM numbers are
   already labelled *preliminary*.
4. Keep the instructor's email that permits AI-assisted writing.

---

## 2. What is completed

**Deliverable A: literature review and gaps** (PDF pp. 2–11)
- 12 peer-reviewed 2025–26 papers, all checked against Crossref; base paper Vyas *et al.*, *J. Process Control* 167
  (2026) 103855, **SJR 2025 0.874, Q1**, with SCImago screenshots as proof (`phase1/figures/`).
- Base-paper analysis, 12 critical summaries, cross-paper comparison table, 6 candidate gaps, and the gap table for
  G1–G3.

**Deliverable B: proposal** (pp. 11–21)
- All 15 required items; architecture diagram (`docs/architecture.png`); baselines B0–B4; research question and
  hypothesis per gap; evaluation plan; milestones, risks, work division and publication direction; section B.16 with
  initial results.

**Deliverable C: technical foundation (this repo)**

| Guideline requirement | Where |
|---|---|
| Finalised architecture | `docs/architecture.png`, `docs/base_paper_mapping.md` |
| Working environment pipeline | `src/emirapl/env/` (TCLab-physics multi-zone plant, 5 faults, mismatch, noise) |
| Baseline with initial results | `src/emirapl/agents/pipeline.py` (base-paper workflow) + `src/emirapl/baselines/`; results in `results/`, `docs/results/` |
| Model integration and provider setup | `src/emirapl/llm/client.py` (Groq/Gemini/Ollama/OpenAI, pacing, quota stop) |
| Tool interfaces | `src/emirapl/tools/` (digital twin rollout, validator), `knowledge.py` |
| State and structured contracts | `src/emirapl/contracts.py` |
| Evaluation dataset / test suite | `configs/suites/` (120-scenario suite + 20-scenario LLM subset), `tests/` (12 tests) |
| End-to-end workflow | `scripts/run_eval.py`; inspect any decision with `scripts/show_trace.py` |
| Clean repo, README, commits from both members | ✅ commits from both members, roughly even |

**Results already in the repo**
- 600 episodes on the 120-scenario suite: no recovery, rule table, DE retune, and the base workflow (scripted proposer)
  with matched and nominal twins.
- Headline: matched twin 0.0 % validated-but-failed vs **19.2 %** with a realistic nominal twin, which is the Gap-1 evidence.
- 15 valid real-LLM episodes (gpt-oss-20b: 5, gpt-oss-120b: 10).

---

## 3. What is left

| Task | Needed for submission? | Effort |
|---|---|---|
| Finish the real-LLM runs on the 20-scenario subset (45 more episodes per model) | No; they're labelled preliminary in the PDF. Nice to have | 3–4 days of free Groq quota, mostly waiting |
| Rebuild the PDF if the LLM runs finish before the deadline | Only if you do the task above | ~30 min |
| Confirm paper [7]'s year with the supervisor | Recommended | 5 min |
| Instructor accepts the GitHub invite | Yes (supervisor access) | — |

Details of the LLM runs: `docs/phase1_remaining_llm_runs.md`. In short:

```bash
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_subset.json --provider groq --model openai/gpt-oss-20b  --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss20b
.venv/Scripts/python scripts/run_eval.py --suite configs/suites/phase1_llm_subset.json --provider groq --model openai/gpt-oss-120b --methods single_llm base_agent_matched base_agent_nominal --run phase1_llm_gptoss120b
```

Runs resume where they stopped. At the daily cap they print `STOPPED: ... daily quota reached` and exit cleanly; run
the same command again the next day. **Your own Groq key gives you a fresh 200k tokens/day per model.**

---

## 4. Set up from a clone (Windows, ~10 min)

```bash
git clone https://github.com/Fatima-Khursheed20/emi-rapl-thermal.git
cd emi-rapl-thermal
git config user.name  "Saleha Muhammad"
git config user.email "219008269+salehamuhammad@users.noreply.github.com"   # links commits to your GitHub account
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"
.venv/Scripts/python -m pytest -q          # expect: 12 passed
copy .env.example .env                      # then put YOUR key: GROQ_API_KEY=...  (https://console.groq.com/keys)
```

To rebuild the Word document you also need Node.js (https://nodejs.org); PDF export uses MS Word.

---

## 5. Rebuild the document after new results

```bash
.venv/Scripts/python scripts/make_report.py --out docs/results     # refresh tables + figures
cd phase1/_build
npm install                                                        # once
python gen_results_json.py ../..                                   # refresh Tables 13-14
node build.js ../Phase1_G3-09_23I-0746.docx ../.. ..
```

Then open the .docx in Word, **update the numbers quoted in the B.16 text** (they come from `phase1/_build/results_text.js`;
edit there and rebuild, or edit in Word directly), and use *File → Save As → PDF* with the same file name. Commit:

```bash
git add results docs/results phase1
git commit -m "Complete Phase-1 LLM runs and refresh results"
git push
```

---

## 6. Where to find things for the viva

- How a decision works: `src/emirapl/agents/pipeline.py` (plan → act → twin → validate → reprompt → fallback).
- Why the twin matters: `src/emirapl/tools/twin.py` (`matched` vs `nominal`) and `tools/validator.py`.
- Two failure cases worth explaining (PDF §B.16): the RETUNE loop on a degraded heater (G2), and a correct sensor offset
  rejected by the nominal twin (G1). Print a trace with
  `python scripts/show_trace.py --run phase1_llm_gptoss20b --scenario p1-z2-heater_degradation-mm00-s0 --method base_agent_matched`.
- Phase-2 plan: PDF §B.6, B.11–B.13; G1 = adaptive EKF + ensemble twin, G2 = counterexample feedback + numeric repair,
  G3 = diagnosis agent.
