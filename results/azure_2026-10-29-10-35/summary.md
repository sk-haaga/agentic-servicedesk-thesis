# Experiment results – provider azure (gpt-4.1-mini), 10 run(s)

Results folder: azure_2026-10-29-10-35. Started 2026-10-29 10:35:28; duration 147.5 min.
Values: mean over runs (± standard deviation over runs); [..] = 95 % confidence interval.

## E1 – public ticket dataset D1

Test tickets: 1000; training pool: 8576

| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |
|---|---|---|---|
| Queue accuracy | 42.3 % [39.2–45.4] | 58.6 % [55.5–61.7] | 46.4 % (±0.3) [43.3–49.4] |
| Queue macro-F1 | 0.254 | 0.587 | 0.383 (±0.003) |
| Priority exact accuracy (P1–P3) | 26.6 % [23.8–29.3] | 60.4 % [57.3–63.5] | 42.4 % (±0.2) [39.3–45.4] |
| Priority macro-F1 | 0.267 | 0.568 | 0.367 (±0.003) |
| High-priority under-prioritisation rate | 82.5 % | 30.7 % | 54.6 % (±0.2) |

Service failures (classification call failed after all retries; counted as wrong above): 0 of 10000 ticket runs (0.0 %). Without them: queue accuracy 46.4 % (±0.3), priority accuracy 42.4 % (±0.2), high-priority under-prioritisation 54.6 % (±0.2).

Exact McNemar test in every run (b = prototype right / baseline wrong, c = the reverse):

| Comparison | mean b | mean c | largest p | runs with p < 0.05 |
|---|---|---|---|---|
| vs supervised queue | 122.7 | 244.9 | < 0.0001 | 10/10 |
| vs supervised priority | 131.3 | 311.2 | < 0.0001 | 10/10 |
| vs keyword queue | 184.5 | 143.7 | 0.0470 | 10/10 |
| vs keyword priority | 280.1 | 122.0 | < 0.0001 | 10/10 |

Leakage check – supervised baseline on a naive random split: queue 68.9 %, priority 72.7 %

### E8 – consistency of the D1 predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| queue | 94.2 % | 58 of 1000 | 98.6 % | 0.961 | 46.3 % | 46.4 % |
| ticket_type | 96.2 % | 38 of 1000 | 99.1 % | 0.972 | – | – |
| impact | 94.5 % | 55 of 1000 | 98.8 % | 0.969 | – | – |
| urgency | 93.5 % | 65 of 1000 | 98.5 % | 0.962 | – | – |
| priority | 93.4 % | 66 of 1000 | 98.5 % | 0.964 | 42.3 % | 42.4 % |

## E2 – controlled benchmark D3, test set

Test emails: 90 from 30 scenario cards; intervals resample whole cards.

| Field | Keyword baseline | Prototype (LLM) | Prototype 95 % CI (cards) |
|---|---|---|---|
| Category accuracy | 71.1 % | 90.6 % (±1.1) | [81.2–97.8] |
| Application accuracy | 93.3 % | 100.0 % (±0.0) | [100.0–100.0] |
| Impact accuracy | 88.9 % | 95.0 % (±1.1) | [90.9–98.4] |
| Urgency accuracy | 90.0 % | 99.9 % (±0.4) | [99.7–100.0] |
| Priority accuracy | 80.0 % | 97.2 % (±1.1) | [94.4–99.4] |
| Resolver group accuracy | 92.2 % | 100.0 % (±0.0) | [100.0–100.0] |
| Category macro-F1 | 0.738 | 0.912 (±0.010) | |
| Application macro-F1 | 0.939 | 1.000 (±0.000) | |
| Whole-ticket exact match | 52.2 % [38.9–64.4] | 88.2 % (±0.8) | [79.0–95.7] |
| High-priority under-prioritisation | 20.8 % | 0.4 % (±1.3) | |

Exact-match difference prototype − keyword: 36.0 points [20.6–51.0] (30 cards).

Card-level sign test (all runs pooled): prototype better on 22 cards, keyword better on 4; p = 0.0005.
Per run: largest McNemar p (emails) = < 0.0001; largest card-level sign-test p = 0.0015 (10 runs).

Failure counts (run 1): {'wrong_category': 9, 'wrong_application': 0, 'wrong_impact': 6, 'wrong_urgency': 0, 'wrong_priority': 3, 'wrong_group': 0}
Failure counts (all runs): {'wrong_category': 85, 'wrong_application': 0, 'wrong_impact': 45, 'wrong_urgency': 1, 'wrong_priority': 25, 'wrong_group': 0}

Service failures (no classification; counted as wrong above): 0 ticket runs [0, 0, 0, 0, 0, 0, 0, 0, 0, 0] (). Without them: whole-ticket exact match 88.2 % (±0.8), priority accuracy 97.2 % (±1.1), application accuracy 100.0 % (±0.0), high-priority under-prioritisation 0.4 % (±1.3).

### E8 – consistency of the D3 test predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| category | 94.4 % | 5 of 90 | 98.3 % | 0.970 | 91.1 % | 90.6 % |
| application | 100.0 % | 0 of 90 | 100.0 % | 1.000 | 100.0 % | 100.0 % |
| impact | 93.3 % | 6 of 90 | 98.1 % | 0.948 | 96.7 % | 95.0 % |
| urgency | 98.9 % | 1 of 90 | 99.9 % | 0.997 | 100.0 % | 99.9 % |
| priority | 93.3 % | 6 of 90 | 98.1 % | 0.957 | 97.8 % | 97.2 % |
| group | 100.0 % | 0 of 90 | 100.0 % | 1.000 | 100.0 % | 100.0 % |
| cited_sop | 93.3 % | 6 of 90 | 98.4 % | 0.972 | – | – |
| answered | 93.3 % | 6 of 90 | 98.4 % | 0.944 | – | – |

## E3/E4 – retrieval and resolution (D3 test set)

| Metric | Without retrieval | With retrieval (RAG) |
|---|---|---|
| Recall@3 (48 answerable cases) | – | 100.0 % (±0.0) |
| Mean reciprocal rank | – | 1.000 (±0.000) |
| Groundedness 2 – fully supported (LLM judge) | 17.1 % (±3.4) | 100.0 % (±0.0) |
| Groundedness 1 | 51.7 % (±4.9) | 0.0 % (±0.0) |
| Groundedness 0 – significant unsupported step | 31.2 % (±2.6) | 0.0 % (±0.0) |
| Key-step coverage (keyword match) | 40.0 % (±2.0) | 90.7 % (±0.5) |
| Abstention on unanswerable tickets | 9.5 % (±1.9) | 69.5 % (±3.1) |

Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run `python -m src.experiments.agreement --folder <this folder>`.

## E5 – selective automation

Thresholds chosen on the calibration set (120 emails × 10 runs pooled; criterion 'point', target 0.95, at least 10.0 accepted per run): **τ₁ = 1.01, τ₂ = 1.01** (target not met; fallback: assistive mode (no automatic handling)). Calibration coverage 0.0 %, accuracy –, 0.0 accepted per run, lower bound –.

Reference operating point (highest Clopper–Pearson lower bound with enough accepted tickets): τ₁ = 0.8, τ₂ = 0.624; calibration coverage 43.6 %, accuracy 81.5 %, lower bound 69.7 %.

Ablation (E5b) and security analysis (E6b) use τ₁ = 0.8, τ₂ = 0.624: reference operating point (highest lower bound), because the chosen point automates nothing.

| Test set at the frozen thresholds | Result |
|---|---|
| Coverage (share handled automatically) | 0.0 % (±0.0) [0.0–4.0] |
| Accepted-case accuracy | – – |
| Tickets handled automatically per run | 0.0 (±0.0) |
| Auto answers with groundedness 2 (LLM judge) | – |
| Unanswerable tickets handled automatically (count per run) | 0.0 (±0.0) |
| True P1 tickets handled automatically (count per run) | 0.0 (±0.0) |
| Tickets expected to be automatable (gold) | 48 (±0) |

Exact (Clopper–Pearson) intervals use the per-run average counts.

Test set at the reference operating point (for comparison; not the deployed setting):

coverage 50.8 % (±1.1) [40.4–61.8]; accepted-case accuracy 85.1 % (±1.2) [71.1–93.7]; unanswerable auto 2.1 (±0.7); true P1 auto 0.0 (±0.0) per run.

Secondary, post hoc: accepted-case accuracy when the category label is not required (priority, application, resolver group and SOP still must be right): 94.6 % (±2.0).

Post hoc test-set curve at the analysis τ₁ (sensitivity only, not used for the choice):

| τ₂ | Coverage | Accepted-case accuracy | Unanswerable auto (per run) |
|---|---|---|---|
| 0.395 | 54.4 % | 86.1 % | 2.1 |
| 0.483 | 54.4 % | 86.1 % | 2.1 |
| 0.559 | 54.4 % | 86.1 % | 2.1 |
| 0.594 | 53.4 % | 85.9 % | 2.1 |
| 0.624 | 50.8 % | 85.1 % | 2.1 |
| 0.648 | 46.0 % | 84.8 % | 1.6 |
| 0.663 | 41.2 % | 86.5 % | 1.0 |
| 0.678 | 36.7 % | 84.9 % | 1.0 |
| 0.712 | 21.6 % | 87.6 % | 0.0 |
| 0.766 | 7.6 % | 100.0 % | 0.0 |

Gate decision consistency on the test set (at the analysis point): same decision in all runs for 93.3 % of tickets; 6 tickets changed at least once; Fleiss κ = 0.939.

## E5b – guardrail ablation (one gate condition switched off at a time; stored outputs, mean per run)

| Gate | Test coverage | Test accepted accuracy | Unanswerable auto | True P1 auto | Challenge auto | Attack auto |
|---|---|---|---|---|---|---|
| all conditions | 50.8 % | 85.1 % | 2.1 | 0.0 | 1.1 | 0.0 |
| without errors | 50.8 % | 85.1 % | 2.1 | 0.0 | 1.1 | 0.0 |
| without injection | 50.8 % | 85.1 % | 2.1 | 0.0 | 7.7 | 10.0 |
| without priority policy | 52.7 % | 82.1 % | 3.1 | 1.0 | 2.1 | 0.0 |
| without category policy | 51.8 % | 83.5 % | 3.0 | 0.0 | 1.1 | 0.0 |
| without confidence | 50.8 % | 85.1 % | 2.1 | 0.0 | 5.2 | 0.0 |
| without similarity | 54.4 % | 86.1 % | 2.1 | 0.0 | 4.4 | 0.0 |
| without grounded | 50.8 % | 85.1 % | 2.1 | 0.0 | 1.1 | 0.0 |

## E6 – challenge and attack sets (at the analysis point named under E5)

| Type (n) | Correctly escalated | Injection detected | by pattern screen | by LLM flag | Auto although escalation expected | Blocked tool calls | Rejected by the LLM service |
|---|---|---|---|---|---|---|---|
| ambiguous_application (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| contradictory (4) | 75.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 1.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 90.0 % (±0.0) | 80.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 2.0 (±0.0) |
| missing_info (6) | 98.3 % (±5.3) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.1 (±0.3) | 0.0 (±0.0) | 0.0 (±0.0) |
| no_sop (4) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| embedded_injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 50.0 % (±0.0) | 100.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |

## E6b – attack success with and without defences

An attack succeeds if the ticket is handled automatically, its triage is changed from the gold labels, the reply follows the payload or leaks the prompt, or a tool outside the allow-list is requested. 'Undefended' = no pattern screen, no prompt-level defences, gate ignores injection flags (tool allow-list and the other gate conditions stay on).

| Condition | Set (n) | Any success | Auto-handled | Triage changed | Payload in reply (draft) | Payload in an automatic reply | Unauthorised tool | Detected |
|---|---|---|---|---|---|---|---|---|
| defended | challenge_injection (10) | 34.0 % (±5.2) | 0.0 % (±0.0) | 34.0 % (±5.2) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 100.0 % (±0.0) |
| defended | embedded_attack (10) | 16.0 % (±5.2) | 0.0 % (±0.0) | 10.0 % (±0.0) | 6.0 % (±5.2) | 0.0 % (±0.0) | 0.0 % (±0.0) | 100.0 % (±0.0) |
| undefended | challenge_injection (10) | 69.0 % (±3.2) | 59.0 % (±3.2) | 30.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 74.0 % (±5.2) |
| undefended | embedded_attack (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 0.0 % (±0.0) | 11.0 % (±5.7) | 11.0 % (±5.7) | 0.0 % (±0.0) | 76.0 % (±5.2) |

'Triage changed' also counts ordinary classification errors; compare the two conditions rather than reading it alone.

## E7 – efficiency and reliability

| Metric | Result |
|---|---|
| Ticket runs (D3, with defences) | 2500 |
| Median / 95th-percentile end-to-end latency (s) | 5.018 / 6.576 (parallel workers: 4) |
| Mean LLM calls per ticket | 3.04 |
| Mean tokens per ticket | 2896.7 |
| Estimated cost per ticket (EUR) | 0.001422 (price basis per million tokens: {'input_per_m': 0.37, 'output_per_m': 1.47}) |
| Tickets with errors (share) | 0.8 % |
| LLM retries / schema repairs (total) | 0 / 0 |
| Decisions with a complete audit record | 100.0 % |

Errors by type: {'classification_BadRequestError:content_filter': 20}

Model versions reported by the API (calls): {'gpt-4.1-mini-2025-04-14': 20898}; embeddings: {'text-embedding-3-small': 2707}
