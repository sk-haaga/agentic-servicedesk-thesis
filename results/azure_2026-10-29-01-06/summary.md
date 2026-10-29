# Experiment results – provider azure (gpt-4.1-mini), 10 run(s)

Results folder: azure_2026-10-29-01-06. Started 2026-10-29 01:06:18; duration 209.9 min.
Values: mean over runs (± standard deviation over runs); [..] = 95 % confidence interval.

## E1 – public ticket dataset D1

Test tickets: 1000; training pool: 8576

| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |
|---|---|---|---|
| Queue accuracy | 42.3 % [39.2–45.4] | 58.6 % [55.5–61.7] | 45.8 % (±0.3) [42.7–48.8] |
| Queue macro-F1 | 0.254 | 0.587 | 0.305 (±0.002) |
| Priority exact accuracy (P1–P3) | 26.6 % [23.8–29.3] | 60.4 % [57.3–63.5] | 41.9 % (±0.3) [38.8–44.9] |
| Priority macro-F1 | 0.267 | 0.568 | 0.275 (±0.002) |
| High-priority under-prioritisation rate | 82.5 % | 30.7 % | 55.0 % (±0.6) |

Exact McNemar test in every run (b = prototype right / baseline wrong, c = the reverse):

| Comparison | mean b | mean c | largest p | runs with p < 0.05 |
|---|---|---|---|---|
| vs supervised queue | 120.9 | 249.0 | < 0.0001 | 10/10 |
| vs supervised priority | 128.7 | 313.8 | < 0.0001 | 10/10 |
| vs keyword queue | 182.2 | 147.3 | 0.1124 | 2/10 |
| vs keyword priority | 276.4 | 123.5 | < 0.0001 | 10/10 |

Leakage check – supervised baseline on a naive random split: queue 68.9 %, priority 72.7 %

### E8 – consistency of the D1 predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| queue | 83.6 % | 164 of 1000 | 97.7 % | 0.928 | 46.6 % | 45.8 % |
| ticket_type | 84.3 % | 157 of 1000 | 97.9 % | 0.927 | – | – |
| impact | 83.6 % | 164 of 1000 | 97.7 % | 0.933 | – | – |
| urgency | 82.6 % | 174 of 1000 | 97.6 % | 0.930 | – | – |
| priority | 82.7 % | 173 of 1000 | 97.6 % | 0.933 | 42.3 % | 41.9 % |

## E2 – controlled benchmark D3, test set

Test emails: 90 from 30 scenario cards; intervals resample whole cards.

| Field | Keyword baseline | Prototype (LLM) | Prototype 95 % CI (cards) |
|---|---|---|---|
| Category accuracy | 71.1 % | 90.6 % (±0.9) | [81.6–97.2] |
| Application accuracy | 93.3 % | 99.2 % (±0.8) | [98.6–99.8] |
| Impact accuracy | 88.9 % | 94.3 % (±1.0) | [90.0–98.0] |
| Urgency accuracy | 90.0 % | 99.2 % (±0.8) | [98.6–99.8] |
| Priority accuracy | 80.0 % | 96.6 % (±1.0) | [93.3–99.1] |
| Resolver group accuracy | 92.2 % | 99.2 % (±0.8) | [98.6–99.8] |
| Category macro-F1 | 0.738 | 0.836 (±0.071) | |
| Application macro-F1 | 0.939 | 0.930 (±0.060) | |
| Whole-ticket exact match | 52.2 % [38.9–64.4] | 87.9 % (±1.1) | [78.9–95.0] |
| High-priority under-prioritisation | 20.8 % | 1.2 % (±2.0) | |

Exact-match difference prototype − keyword: 35.7 points [20.3–50.7] (30 cards).

Card-level sign test (all runs pooled): prototype better on 21 cards, keyword better on 3; p = 0.0003.
Per run: largest McNemar p (emails) = < 0.0001; largest card-level sign-test p = 0.0009 (10 runs).

Failure counts (run 1): {'wrong_category': 7, 'wrong_application': 0, 'wrong_impact': 4, 'wrong_urgency': 0, 'wrong_priority': 2, 'wrong_group': 0}
Failure counts (all runs): {'wrong_category': 85, 'wrong_application': 7, 'wrong_impact': 51, 'wrong_urgency': 7, 'wrong_priority': 31, 'wrong_group': 7}

### E8 – consistency of the D3 test predictions across runs

| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |
|---|---|---|---|---|---|---|
| category | 88.9 % | 10 of 90 | 98.1 % | 0.960 | 92.2 % | 90.6 % |
| application | 93.3 % | 6 of 90 | 99.2 % | 0.983 | 100.0 % | 99.2 % |
| impact | 90.0 % | 9 of 90 | 98.3 % | 0.944 | 94.4 % | 94.3 % |
| urgency | 93.3 % | 6 of 90 | 99.2 % | 0.977 | 100.0 % | 99.2 % |
| priority | 90.0 % | 9 of 90 | 98.3 % | 0.954 | 96.7 % | 96.6 % |
| group | 93.3 % | 6 of 90 | 99.2 % | 0.982 | 100.0 % | 99.2 % |
| cited_sop | 81.1 % | 17 of 90 | 97.4 % | 0.947 | – | – |
| answered | 74.4 % | 23 of 90 | 96.6 % | 0.868 | – | – |

## E3/E4 – retrieval and resolution (D3 test set)

| Metric | Without retrieval | With retrieval (RAG) |
|---|---|---|
| Recall@3 (48 answerable cases) | – | 99.8 % (±0.7) |
| Mean reciprocal rank | – | 0.998 (±0.007) |
| Groundedness 2 – fully supported (LLM judge) | 17.4 % (±3.4) | 100.0 % (±0.0) |
| Groundedness 1 | 51.4 % (±5.1) | 0.0 % (±0.0) |
| Groundedness 0 – significant unsupported step | 31.1 % (±2.0) | 0.0 % (±0.0) |
| Key-step coverage (keyword match) | 39.8 % (±1.5) | 89.2 % (±1.5) |
| Abstention on unanswerable tickets | 11.7 % (±3.3) | 72.6 % (±2.0) |

Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run `python -m src.experiments.agreement --folder <this folder>`.

## E5 – selective automation

Thresholds chosen on the calibration set (120 emails × 10 runs pooled; criterion 'point', target 0.95, at least 10.0 accepted per run): **τ₁ = 1.01, τ₂ = 1.01** (target not met; fallback: assistive mode (no automatic handling)). Calibration coverage 0.0 %, accuracy –, 0.0 accepted per run, lower bound –.

Reference operating point (highest Clopper–Pearson lower bound with enough accepted tickets): τ₁ = 0.9, τ₂ = 0.624; calibration coverage 42.1 %, accuracy 82.8 %, lower bound 70.9 %.

Ablation (E5b) and security analysis (E6b) use τ₁ = 0.9, τ₂ = 0.624: reference operating point (highest lower bound), because the chosen point automates nothing.

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

coverage 48.9 % (±2.2) [38.2–59.7]; accepted-case accuracy 86.4 % (±2.1) [72.7–94.8]; unanswerable auto 1.7 (±0.8); true P1 auto 0.0 (±0.0) per run.

Post hoc test-set curve at the analysis τ₁ (sensitivity only, not used for the choice):

| τ₂ | Coverage | Accepted-case accuracy | Unanswerable auto (per run) |
|---|---|---|---|
| 0.0 | 52.8 % | 87.4 % | 1.7 |
| 0.483 | 52.8 % | 87.4 % | 1.7 |
| 0.561 | 52.8 % | 87.4 % | 1.7 |
| 0.597 | 51.7 % | 87.1 % | 1.7 |
| 0.624 | 48.9 % | 86.4 % | 1.7 |
| 0.65 | 43.9 % | 86.0 % | 1.2 |
| 0.662 | 40.1 % | 86.1 % | 1.0 |
| 0.678 | 36.3 % | 84.7 % | 1.0 |
| 0.711 | 22.7 % | 90.8 % | 0.0 |
| 0.767 | 6.8 % | 100.0 % | 0.0 |

Gate decision consistency on the test set: same decision in all runs for 100.0 % of tickets; 0 tickets changed at least once; Fleiss κ = 1.000.

## E5b – guardrail ablation (one gate condition switched off at a time; stored outputs, mean per run)

| Gate | Test coverage | Test accepted accuracy | Unanswerable auto | True P1 auto | Challenge auto | Attack auto |
|---|---|---|---|---|---|---|
| all conditions | 48.9 % | 86.4 % | 1.7 | 0.0 | 1.0 | 0.0 |
| without errors | 48.9 % | 86.4 % | 1.7 | 0.0 | 1.0 | 0.0 |
| without injection | 48.9 % | 86.4 % | 1.7 | 0.0 | 7.7 | 9.2 |
| without priority policy | 50.7 % | 83.4 % | 2.6 | 0.9 | 2.0 | 0.0 |
| without category policy | 49.4 % | 85.4 % | 2.2 | 0.0 | 1.0 | 0.0 |
| without confidence | 49.8 % | 84.8 % | 2.5 | 0.0 | 5.2 | 0.0 |
| without similarity | 52.8 % | 87.4 % | 1.7 | 0.0 | 2.0 | 0.0 |
| without grounded | 48.9 % | 86.4 % | 1.7 | 0.0 | 1.0 | 0.0 |

## E6 – challenge and attack sets (at the analysis point named under E5)

| Type (n) | Correctly escalated | Injection detected | by pattern screen | by LLM flag | Auto although escalation expected | Blocked tool calls | Rejected by the LLM service |
|---|---|---|---|---|---|---|---|
| ambiguous_application (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| contradictory (4) | 75.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 1.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 90.0 % (±0.0) | 80.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 2.0 (±0.0) |
| missing_info (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| no_sop (4) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |
| embedded_injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 50.0 % (±0.0) | 100.0 % (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) | 0.0 (±0.0) |

## E6b – attack success with and without defences

An attack succeeds if the ticket is handled automatically, its triage is changed from the gold labels, the reply follows the payload or leaks the prompt, or a tool outside the allow-list is requested. 'Undefended' = no pattern screen, no prompt-level defences, gate ignores injection flags (tool allow-list and the other gate conditions stay on).

| Condition | Set (n) | Any success | Auto-handled | Triage changed | Payload in reply | Unauthorised tool | Detected |
|---|---|---|---|---|---|---|---|
| defended | challenge_injection (10) | 34.0 % (±5.2) | 0.0 % (±0.0) | 34.0 % (±5.2) | 0.0 % (±0.0) | 0.0 % (±0.0) | 100.0 % (±0.0) |
| defended | embedded_attack (10) | 18.0 % (±4.2) | 0.0 % (±0.0) | 10.0 % (±0.0) | 8.0 % (±4.2) | 0.0 % (±0.0) | 100.0 % (±0.0) |
| undefended | challenge_injection (10) | 66.0 % (±5.2) | 56.0 % (±5.2) | 30.0 % (±0.0) | 0.0 % (±0.0) | 0.0 % (±0.0) | 69.0 % (±3.2) |
| undefended | embedded_attack (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 0.0 % (±0.0) | 3.0 % (±4.8) | 0.0 % (±0.0) | 80.0 % (±0.0) |

'Triage changed' also counts ordinary classification errors; compare the two conditions rather than reading it alone.

## E7 – efficiency and reliability

| Metric | Result |
|---|---|
| Ticket runs (D3, with defences) | 2500 |
| Median / 95th-percentile end-to-end latency (s) | 6.931 / 10.421 (parallel workers: 4) |
| Mean LLM calls per ticket | 2.98 |
| Mean tokens per ticket | 2849.1 |
| Estimated cost per ticket (EUR) | 0.0014 (price basis per million tokens: {'input_per_m': 0.37, 'output_per_m': 1.47}) |
| Tickets with errors (share) | 2.7 % |
| LLM retries / schema repairs (total) | 6436 / 0 |
| Decisions with a complete audit record | 100.0 % |

Errors by type: {'resolution_RateLimitError:rate_limit_exceeded': 34, 'classification_BadRequestError:content_filter': 20, 'classification_RateLimitError:rate_limit_exceeded': 13}

Model versions reported by the API (calls): {'gpt-4.1-mini-2025-04-14': 20613}; embeddings: {'text-embedding-3-small': 2698}
