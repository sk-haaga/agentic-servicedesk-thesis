# Guardrailed agentic AI for IT service desk triage

Prototype and evaluation code for the Master's thesis *Guardrailed Agentic AI for IT Service Desk Triage:
Design and Evaluation of a Human-in-the-Loop Prototype Without Organisational Ticket Data*
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
| `src/data_prep/` | Preparation of the public dataset D1 and the controlled benchmark D2 (scenario cards) |
| `src/analysis/` | Analysis of the public ServiceNow incident log D3 |
| `src/experiments/` | Experiments E1–E7, metrics, report, judge agreement |
| `config/` | Settings (thresholds) and service catalogues |
| `kb/sops/` | 21 SOP / knowledge articles (author-written) |
| `data/d2/` | Controlled benchmark: 150 labelled emails (`benchmark.jsonl`, `emails/*.eml`) |
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

* `aa_dataset-tickets-multi-lang-5-2-50-version.csv` – Bueck (2025), Hugging Face, CC BY-NC 4.0
* `incident_event_log.csv` – Amaral, Fantinato & Peres (2018), UCI, CC BY 4.0

```powershell
python -m src.data_prep.prepare_d1          # D1 splits (leakage-free, near-duplicate groups kept together)
python -m src.data_prep.build_d2            # D2 benchmark from the scenario cards
python -m src.analysis.d3_incident_log      # D3 problem analysis -> results/d3_summary.json
```

## Run the prototype

```powershell
python -m src.servicedesk.cli data\d2\emails\C01-1.eml data\d2\emails\C11-1.eml
streamlit run src\servicedesk\console.py                      # review console (Inbox + Review queue)
uvicorn src.servicedesk.itsm.api:app --port 8000              # mock ITSM REST API (optional)
```

Set `LLM_PROVIDER=fake` in `.env` to try everything offline with a deterministic keyword stand-in.

## Run the experiments

```powershell
python -m src.experiments.run --provider fake --runs 1 --limit 10   # 1-minute offline smoke test
python -m src.experiments.run --provider azure --runs 3              # full evaluation (about 1-2 h, a few euros)
```

Results go to `results/<provider>/`: `summary.md` (values for the thesis tables), `summary.json`,
per-case files and `figures/`. For the groundedness agreement check, fill `author_score` in
`results/azure/e4_blind_scoring_sheet.csv` and run `python -m src.experiments.agreement --provider azure`.

## Safety design (summary)

* Email text is untrusted: personal data masked, text delimited, injection patterns screened.
* Priority and routing are deterministic rules; P1 and security incidents always go to a human.
* Agents can only call allow-listed tools (`search_sops`, `request_human_review`); there is no tool that
  changes systems. Blocked tool requests are logged.
* Answers must cite a retrieved SOP; otherwise the agent abstains.
* Email sending is simulated; nothing is sent to real users.
