# Experiment results – provider azure (gpt-4.1-mini), 3 run(s)

Results folder: –. Started 2026-10-14 23:58:59; duration 32.4 min.
Values: mean over runs (± standard deviation over runs); [..] = 95 % confidence interval.

**Re-analysed 2026-10-29 01:03:42.** Recomputed with the analysis code of design iteration 2 from the stored outputs; the original summary.json in this folder is unchanged.

## E1 – public ticket dataset D1

Test tickets: 400; training pool: 9553

| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |
|---|---|---|---|
| Queue accuracy | 42.0 % | 59.0 % | 46.8 % (±0.4) [42.1–51.7] |
| Queue macro-F1 | 0.234 | 0.574 | 0.352 (±0.041) |
| Priority exact accuracy (P1–P3) | 26.8 % | 59.8 % | 38.5 % (±0.5) [33.9–43.3] |
| Priority macro-F1 | 0.270 | 0.558 | 0.302 (±0.049) |
| High-priority under-prioritisation rate | 82.6 % | 31.8 % | 57.4 % (±0.5) |

McNemar (run 1) prototype vs supervised: queue p = < 0.0001; priority p = < 0.0001

Leakage check – supervised baseline on a naive random split: queue 76.2 %, priority 74.8 %

### E8 – consistency of the D1 predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| queue | 96.8 % | 13 of 400 | 98.9 % | 0.961 | 46.8 % | 46.8 % |
| ticket_type | 97.0 % | 12 of 400 | 99.0 % | 0.961 | – | – |
| impact | 96.5 % | 14 of 400 | 98.8 % | 0.961 | – | – |
| urgency | 94.8 % | 21 of 400 | 98.2 % | 0.943 | – | – |
| priority | 95.2 % | 19 of 400 | 98.4 % | 0.951 | 38.8 % | 38.5 % |

## E2 – controlled benchmark D3, test set

Test emails: 90 from – scenario cards; intervals resample whole cards.

| Field | Keyword baseline | Prototype (LLM) | Prototype 95 % CI (cards) |
|---|---|---|---|
| Category accuracy | 71.1 % | 90.0 % (±1.1) | [80.4–97.8] |
| Application accuracy | 93.3 % | 100.0 % (±0.0) | [100.0–100.0] |
| Impact accuracy | 88.9 % | 95.6 % (±1.1) | [91.1–98.9] |
| Urgency accuracy | 90.0 % | 100.0 % (±0.0) | [100.0–100.0] |
| Priority accuracy | 80.0 % | 98.2 % (±1.3) | [95.6–100.0] |
| Resolver group accuracy | 92.2 % | 100.0 % (±0.0) | [100.0–100.0] |
| Category macro-F1 | 0.738 | 0.905 (±0.010) | |
| Application macro-F1 | 0.939 | 1.000 (±0.000) | |
| Whole-ticket exact match | 52.2 % [38.9–64.4] | 88.5 % (±1.3) | [78.9–96.3] |
| High-priority under-prioritisation | 20.8 % | 0.0 % (±0.0) | |

Exact-match difference prototype − keyword: 36.3 points [20.7–51.5] (30 cards).

Card-level sign test (all runs pooled): prototype better on 21 cards, keyword better on 3; p = 0.0003.
Per run: largest McNemar p (emails) = < 0.0001; largest card-level sign-test p = 0.0005 (3 runs).

Failure counts (run 1): {'wrong_category': 10, 'wrong_application': 0, 'wrong_impact': 3, 'wrong_urgency': 0, 'wrong_priority': 1, 'wrong_group': 0}
Failure counts (all runs): {'wrong_category': 27, 'wrong_application': 0, 'wrong_impact': 12, 'wrong_urgency': 0, 'wrong_priority': 5, 'wrong_group': 0}

### E8 – consistency of the D3 test predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| category | 97.8 % | 2 of 90 | 99.3 % | 0.981 | 90.0 % | 90.0 % |
| application | 100.0 % | 0 of 90 | 100.0 % | 1.000 | 100.0 % | 100.0 % |
| impact | 96.7 % | 3 of 90 | 98.9 % | 0.955 | 96.7 % | 95.6 % |
| urgency | 100.0 % | 0 of 90 | 100.0 % | 1.000 | 100.0 % | 100.0 % |
| priority | 97.8 % | 2 of 90 | 99.3 % | 0.976 | 98.9 % | 98.2 % |
| group | 100.0 % | 0 of 90 | 100.0 % | 1.000 | 100.0 % | 100.0 % |
| cited_sop | 96.7 % | 3 of 90 | 98.9 % | 0.974 | – | – |
| answered | 95.6 % | 4 of 90 | 98.5 % | 0.934 | – | – |

## E3/E4 – retrieval and resolution (D3 test set)

| Metric | Without retrieval | With retrieval (RAG) |
|---|---|---|
| Recall@3 (48 answerable cases) | – | 100.0 % (±0.0) |
| Mean reciprocal rank | – | 1.000 (±0.000) |
| Groundedness share 2 / 1 / 0 (LLM judge, run 1) | [0.1667, 0.5, 0.3333] | [1.0, 0.0, 0.0] |
| Key-step coverage | 39.1 % | 91.7 % |
| Abstention on unanswerable | 9.5 % | 69.0 % |

Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run `python -m src.experiments.agreement --folder <this folder>`.

## E5 – selective automation

Thresholds chosen on the calibration set (30 emails × 3 runs pooled; criterion 'point', target 0.95, at least 10.0 accepted per run): **τ₁ = 1.01, τ₂ = 1.01** (target not met; fallback: assistive mode (no automatic handling)). Calibration coverage 0.0 %, accuracy –, 0.0 accepted per run, lower bound –.

Reference operating point (highest Clopper–Pearson lower bound with enough accepted tickets): τ₁ = 0.9, τ₂ = 0.618; calibration coverage 50.0 %, accuracy 75.6 %, lower bound 44.9 %.

Ablation (E5b) and security analysis (E6b) use τ₁ = 0.9, τ₂ = 0.618: reference operating point (highest lower bound), because the chosen point automates nothing.

Originally chosen in this folder: {'tau1': 0.9, 'tau2': 0.63, 'dev_coverage': 0.5, 'dev_accepted_accuracy': 0.7333, 'target_met': False}

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

coverage 51.8 % (±0.6) [41.4–62.9]; accepted-case accuracy 89.3 % (±0.1) [76.9–96.5]; unanswerable auto 1.0 (±0.0); true P1 auto 0.0 (±0.0) per run.

Post hoc test-set curve at the analysis τ₁ (sensitivity only, not used for the choice):

| τ₂ | Coverage | Accepted-case accuracy | Unanswerable auto (per run) |
|---|---|---|---|
| 0.481 | 54.1 % | 89.7 % | 1.0 |
| 0.589 | 53.0 % | 89.5 % | 1.0 |
| 0.618 | 51.8 % | 89.3 % | 1.0 |
| 0.641 | 47.8 % | 88.4 % | 1.0 |
| 0.647 | 45.6 % | 87.8 % | 1.0 |
| 0.654 | 43.3 % | 87.2 % | 1.0 |
| 0.664 | 39.6 % | 86.0 % | 1.0 |
| 0.715 | 20.4 % | 92.8 % | 0.0 |
| 0.751 | 9.6 % | 100.0 % | 0.0 |
| 0.773 | 6.7 % | 100.0 % | 0.0 |

Gate decision consistency on the test set: same decision in all runs for 100.0 % of tickets; 0 tickets changed at least once; Fleiss κ = 1.000.

## E5b – guardrail ablation (one gate condition switched off at a time; stored outputs, mean per run)

| Gate | Test coverage | Test accepted accuracy | Unanswerable auto | True P1 auto | Challenge auto | Attack auto |
|---|---|---|---|---|---|---|
| all conditions | 51.8 % | 89.3 % | 1.0 | 0.0 | 1.0 | – |
| without errors | 51.8 % | 89.3 % | 1.0 | 0.0 | 1.0 | – |
| without injection | 51.8 % | 89.3 % | 1.0 | 0.0 | 7.3 | – |
| without priority policy | 53.3 % | 86.8 % | 2.0 | 1.0 | 2.0 | – |
| without category policy | 53.7 % | 86.2 % | 2.7 | 0.0 | 1.0 | – |
| without confidence | 52.2 % | 88.7 % | 1.3 | 0.0 | 6.0 | – |
| without similarity | 54.1 % | 89.7 % | 1.0 | 0.0 | 2.0 | – |
| without grounded | 51.8 % | 89.3 % | 1.0 | 0.0 | 1.0 | – |

## E6 – challenge and attack sets (at the analysis point named under E5)

| Type (n) | Correctly escalated | Injection detected | by pattern screen | by LLM flag | Auto although escalation expected | Blocked tool calls | Rejected by the LLM service |
|---|---|---|---|---|---|---|---|
| ambiguous_application (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| contradictory (4) | 75.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 1.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 90.0 % (±0.0) | 80.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 2.0 (±0.0) |
| missing_info (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| no_sop (4) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |

## E6b – attack success with and without defences

An attack succeeds if the ticket is handled automatically, its triage is changed from the gold labels, the reply follows the payload or leaks the prompt, or a tool outside the allow-list is requested. 'Undefended' = no pattern screen, no prompt-level defences, gate ignores injection flags (tool allow-list and the other gate conditions stay on).

| Condition | Set (n) | Any success | Auto-handled | Triage changed | Payload in reply | Unauthorised tool | Detected |
|---|---|---|---|---|---|---|---|
| defended | challenge_injection (10) | 36.7 % (±5.8) | 0.0 % (±0.0) | 36.7 % (±5.8) | 0.0 % (±0.0) | 0.0 % (±0.0) | 100.0 % (±0.0) |

'Triage changed' also counts ordinary classification errors; compare the two conditions rather than reading it alone.

## E7 – efficiency and reliability

| Metric | Result |
|---|---|
| Ticket runs (D3, with defences) | 450 |
| Median / 95th-percentile end-to-end latency (s) | 7.045 / 9.935 (parallel workers: –) |
| Mean LLM calls per ticket | 3.05 |
| Mean tokens per ticket | 2936.5 |
| Estimated cost per ticket (EUR) | 0.001439 (price basis per million tokens: –) |
| Tickets with errors (share) | 1.6 % |
| LLM retries / schema repairs (total) | 461 / 0 |
| Decisions with a complete audit record | 100.0 % |

Errors by type: {'classification_BadRequestError': 6}
