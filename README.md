# Guardrailed agentic AI for IT service desk triage

Prototype and evaluation code for the Master's thesis *Guardrailed Agentic AI for IT Service Desk Triage:
Design and Evaluation of a Human-in-the-Loop Prototype*
(S Kumar, Technical University of Košice & Haaga-Helia University of Applied Sciences, 2026).

The prototype turns an IT-support email into a ticket, classifies it (category, application, impact,
urgency), computes priority P1–P3 with an explicit impact × urgency matrix, routes it to a resolver group,
retrieves standard operating procedures (SOPs) and drafts an SOP-grounded answer. A confidence and policy
gate decides whether the answer is eligible for automatic handling (P2/P3 only, sending simulated) or the
ticket goes to a human reviewer. Every step is written to an audit log.

```
email → intake & guard → create ticket → classifier agent → priority rules → routing rules
      → knowledge agent (RAG) → resolver agent (allow-listed tools) → confidence & policy gate
      → auto-eligible response | human review (LangGraph interrupt) 
```

## Repository layout

| Path | Content |
|---|---|
| `src/servicedesk/` | The prototype: workflow (LangGraph), agents, rules, gate, guard, tools, LLM providers, mock ITSM API, review console |
| `src/baselines/` | Keyword baseline and supervised TF-IDF + logistic-regression baseline |
| `src/data_prep/` | Preparation of the public ticket dataset D1 and the controlled benchmark D3 (scenario cards) |
| `src/analysis/` | Analysis of the public ServiceNow incident log D2 |
| `src/experiments/` | Experiments E1–E8, metrics, report, judge agreement |
| `config/` | Settings (thresholds) and service catalogues |
| `kb/sops/` | 21 SOP / knowledge articles (author-written) |
| `data/d3/` | Controlled benchmark: 250 labelled emails (`benchmark.jsonl`, `emails/*.eml`) |
| `results/` | One folder per evaluation run (see `results/README.md`) |
| `tests/` | Offline tests (no API key needed) |

## Setup (Windows, PowerShell)

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env      # then edit .env: Azure endpoint, key and deployment names
python -m pytest -q         # offline tests, should all pass
```

On macOS/Linux use `python3 -m venv .venv` and `source .venv/bin/activate`.

## Data

Public data is not included. Download into `data/raw/` (see `data/raw/README.md`):

* `aa_dataset-tickets-multi-lang-5-2-50-version.csv` – Bück (2025), Hugging Face, CC BY-NC 4.0
* `incident_event_log.csv` – Amaral, Fantinato & Peres (2018), UCI, CC BY 4.0

```powershell
python -m src.data_prep.prepare_d1          # D1 splits (leakage-free, near-duplicate groups kept together)
python -m src.data_prep.build_d3            # D3 benchmark from the scenario cards
python -m src.analysis.d2_incident_log      # D2 problem analysis -> results/d2_summary.json
```

## Run the prototype

```powershell
python -m src.servicedesk.cli data\d3\emails\C01-1.eml data\d3\emails\C11-1.eml
streamlit run src\servicedesk\console.py                      # review console (Inbox + Review queue)
uvicorn src.servicedesk.itsm.api:app --port 8000              # mock ITSM REST API (optional)
```

Set `LLM_PROVIDER=fake` in `.env` to try everything offline with a deterministic keyword stand-in.

## Run the experiments

```powershell
python -m src.experiments.run --provider fake --runs 2 --limit 10    # 1-minute offline smoke test
python -m src.experiments.run --provider azure                       # full evaluation, 10 runs (several hours)
python -m src.experiments.run --reanalyse results\azure_2026-10-15-15-19   # recompute analyses, no LLM calls
```

| Experiment | Data | What it measures |
|---|---|---|
| E1 | D1 test sample | Triage vs keyword and supervised baselines; McNemar test in every run |
| E2 | D3 test set | Triage field by field; intervals and paired tests by scenario card |
| E3/E4 | D3 test set | Retrieval (Recall@3, MRR); RAG ablation (groundedness, key steps, abstention) |
| E5 | D3 calibration → test | Thresholds chosen on the calibration set (rule in `config/settings.yaml`), frozen, applied to test |
| E5b | stored outputs | Guardrail ablation: each gate condition switched off in turn |
| E6 / E6b | D3 challenge and attack sets | Escalation and detection; attack success with and without defences |
| E7 | all runs | Latency, LLM calls, tokens, cost, errors, audit completeness |
| E8 | D1 and D3 test | Consistency of outputs across the repeated runs (agreement, Fleiss κ) |

Every evaluation writes to a new folder `results/<provider>_YYYY-MM-DD-HH-MM/`, so earlier results are
never overwritten. It contains `summary.md` (values for the thesis tables), `summary.json`,
`run_manifest.json` (model versions reported by the API, settings, package versions, git commit, data
hashes), the per-case files and `figures/`. For the groundedness agreement check, fill `author_score` in
`<folder>/e4_blind_scoring_sheet.csv` and run `python -m src.experiments.agreement --folder <folder>`.

## Safety design (summary)

* Email text is untrusted: personal data masked, text delimited, injection patterns screened.
* Priority and routing are deterministic rules; P1 and security incidents always go to a human.
* Gate thresholds are chosen on a calibration set with a sample-size rule; if the accuracy target cannot
  be shown, the gate stays in assistive mode (no automatic handling).
* Agents can only call allow-listed tools (`search_sops`, `request_human_review`); there is no tool that
  changes systems. Blocked tool requests are logged.
* Answers must cite a retrieved SOP; otherwise the agent abstains.
* Email sending is simulated; nothing is sent to real users.
