# E9: few-shot triage on D1 (added after the main evaluation)

Model gpt-4.1-mini, 10 runs per condition, 1000 test tickets, examples drawn from 8576 training tickets (seed 42).

| System | Queue accuracy | Priority accuracy | P1 under-prioritisation |
|---|---|---|---|
| Keyword baseline | 42.3% | 26.6% | 82.5% |
| Supervised baseline | 58.6% | 60.4% | 30.7% |
| Prototype, 12 examples (k1) | 38.0% ± 0.2% | 41.4% ± 0.2% | 56.0% |
| Prototype, 36 examples (k3) | 40.8% ± 0.2% | 41.8% ± 0.2% | 57.2% |

## Difference to the prototype without examples (paired over tickets)

| Condition | Field | Few-shot | Zero-shot | Difference [95 % interval] | McNemar p (first runs) |
|---|---|---|---|---|---|
| k1 | queue | 38.0% | 45.8% | -7.8 points [-11.3, -4.2] | 0.0001 |
| k1 | priority | 41.4% | 41.9% | -0.5 points [-2.4, +1.4] | 0.9204 |
| k3 | queue | 40.8% | 45.8% | -5.0 points [-8.7, -1.2] | 0.0219 |
| k3 | priority | 41.8% | 41.9% | -0.1 points [-2.2, +1.9] | 0.8546 |

## Tests against the baselines (runs with p < 0.05 of all runs)

- k1, vs_supervised_queue: 10 of 10 (largest p = 0.0000)
- k1, vs_supervised_priority: 10 of 10 (largest p = 0.0000)
- k1, vs_keyword_queue: 5 of 10 (largest p = 0.0573)
- k1, vs_keyword_priority: 10 of 10 (largest p = 0.0000)
- k3, vs_supervised_queue: 10 of 10 (largest p = 0.0000)
- k3, vs_supervised_priority: 10 of 10 (largest p = 0.0000)
- k3, vs_keyword_queue: 0 of 10 (largest p = 0.5924)
- k3, vs_keyword_priority: 10 of 10 (largest p = 0.0000)

Service failures (no classification): k1: 0, k3: 0
