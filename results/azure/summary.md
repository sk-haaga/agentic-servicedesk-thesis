# Experiment results – provider azure (gpt-4.1-mini), 3 run(s)

Started 2026-10-15 15:19:59; duration 32.3 min. Values: mean (± standard deviation over runs).

## E1 – public ticket dataset D1 (thesis Table e1)

Test tickets: 400; training pool: 9553

| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |
|---|---|---|---|
| Queue accuracy | 42.0 % | 59.0 % | 47.2 % (±0.2) |
| Queue macro-F1 | 0.234 | 0.574 | 0.354 (±0.044) |
| Priority exact accuracy (P1–P3) | 26.8 % | 59.8 % | 39.8 % (±0.2) |
| Priority macro-F1 | 0.270 | 0.558 | 0.314 (±0.047) |
| High-priority under-prioritisation rate | 82.6 % | 31.8 % | 56.9 % (±0.5) |

McNemar (run 1) prototype vs supervised: queue p = 0.0001; priority p = 0.0000
Leakage check – supervised baseline on a naive random split: queue 76.2 %, priority 74.8 %

## E2 – controlled benchmark D2 test set (thesis Table e2)

| Field | Keyword baseline | Prototype (LLM) |
|---|---|---|
| Category accuracy | 71.1 % | 90.4 % (±1.3) |
| Category macro-F1 | 0.738 | 0.910 (±0.012) |
| Application accuracy | 93.3 % | 100.0 % (±0.0) |
| Application macro-F1 | 0.939 | 1.000 (±0.000) |
| Impact accuracy | 88.9 % | 95.6 % (±0.0) |
| Urgency accuracy | 90.0 % | 100.0 % (±0.0) |
| Priority exact accuracy | 80.0 % | 98.5 % (±0.6) |
| Resolver-group accuracy | 92.2 % | 100.0 % (±0.0) |
| Whole-ticket exact match | 52.2 % | 88.9 % (±1.9) |
| High-priority under-prioritisation rate | 20.8 % | 0.0 % (±0.0) |

McNemar exact match prototype vs keyword (run 1): p = 0.0000
Failure counts (run 1): {'wrong_application': 0, 'wrong_category': 8, 'wrong_impact': 4, 'wrong_urgency': 0, 'wrong_priority': 1, 'wrong_group': 0}

## E3/E4 – retrieval and resolution (thesis Table e34)

| Metric | Without retrieval | With retrieval (RAG) |
|---|---|---|
| Recall@3 (answerable cases) | – | 100.0 % (±0.0) |
| Mean reciprocal rank | – | 1.000 (±0.000) |
| Groundedness share 2 / 1 / 0 (LLM judge) | [0.125, 0.5208, 0.3542] | [1.0, 0.0, 0.0] |
| Mean key-step coverage | 39.6 % | 90.3 % |
| Abstention accuracy (unanswerable) | 9.5 % | 73.8 % |

Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run `python -m src.experiments.agreement`.

## E5 – selective automation (thesis Table e5, Figure riskcov)

Chosen on development set: {'tau1': 0.9, 'tau2': 0.769, 'dev_coverage': 0.0667, 'dev_accepted_accuracy': 1.0, 'target_met': True}

| Metric | Result |
|---|---|
| Thresholds τ₁ / τ₂ | 0.9 / 0.769 |
| Coverage (auto-eligible share) | 6.7 % (±0.0) |
| Accepted-case accuracy | 100.0 % (±0.0) |
| Auto-eligible answers with groundedness 2 (run 1) | 100.0 % |
| Unanswerable tickets handled automatically (count) | 0.000 (±0.000) |
| True P1 tickets handled automatically (count) | 0.000 (±0.000) |
| Tickets expected to be automatable (gold) | 48.000 (±0.000) |

## E6 – challenge set (thesis Table e6)

| Challenge type (n) | Correctly escalated | Injection detected | Auto-handled although escalation expected (count) | Blocked tool calls | Rejected by the LLM service |
|---|---|---|---|---|---|
| ambiguous_application (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.000 (±0.000) | 0.000 (±0.000) | 0.000 (±0.000) |
| contradictory (4) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.000 (±0.000) | 0.000 (±0.000) | 0.000 (±0.000) |
| injection (10) | 100.0 % (±0.0) | 100.0 % (±0.0) | 0.000 (±0.000) | 0.000 (±0.000) | 2.000 (±0.000) |
| missing_info (6) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.000 (±0.000) | 0.000 (±0.000) | 0.000 (±0.000) |
| no_sop (4) | 100.0 % (±0.0) | 0.0 % (±0.0) | 0.000 (±0.000) | 0.000 (±0.000) | 0.000 (±0.000) |

## E7 – efficiency and reliability (thesis Table e7)

| Metric | Result |
|---|---|
| Median / 95th-percentile end-to-end latency (s) | 7.04 / 9.875 |
| Mean LLM calls per ticket | 3.02 |
| Mean tokens per ticket | 2887.2 |
| Estimated cost per ticket (EUR) | 0.001415 |
| Tickets with errors (share) | 1.6 % |
| LLM retries / schema repairs (total) | 340 / 0 |
| Decisions with a complete audit record | 100.0 % |
