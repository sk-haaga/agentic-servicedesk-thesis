"""Evaluation metrics (thesis chapter 3.4.2 and Appendix 6)."""
from __future__ import annotations

import math

import numpy as np
from sklearn.metrics import accuracy_score, cohen_kappa_score, confusion_matrix, f1_score


def acc(y, p) -> float:
    return float(accuracy_score(y, p)) if len(y) else float("nan")


def macro_f1(y, p) -> float:
    return float(f1_score(y, p, average="macro", zero_division=0)) if len(y) else float("nan")


def under_prioritisation(y, p) -> float:
    """Share of true P1 tickets predicted as P2 or P3."""
    pairs = [(a, b) for a, b in zip(y, p) if a == "P1"]
    return float(sum(b != "P1" for _, b in pairs) / len(pairs)) if pairs else float("nan")


def bootstrap_ci(correct: list[bool], n: int = 2000, seed: int = 42) -> tuple[float, float]:
    """95 % percentile bootstrap interval for a mean of 0/1 outcomes (Efron & Tibshirani 1993)."""
    if not correct:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    arr = np.array(correct, dtype=float)
    means = rng.choice(arr, size=(n, len(arr)), replace=True).mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def mcnemar(correct_a: list[bool], correct_b: list[bool]) -> dict:
    """Exact (binomial) McNemar test on paired correctness (McNemar 1947; Dietterich 1998)."""
    b = sum(1 for x, y in zip(correct_a, correct_b) if x and not y)
    c = sum(1 for x, y in zip(correct_a, correct_b) if y and not x)
    n = b + c
    if n == 0:
        return {"b": b, "c": c, "p": 1.0}
    k = min(b, c)
    p = sum(math.comb(n, i) for i in range(0, k + 1)) / 2 ** n * 2
    return {"b": b, "c": c, "p": min(1.0, p)}


def recall_at_k(expected: list[str], retrieved: list[list[str]], k: int = 3) -> float:
    pairs = [(e, r) for e, r in zip(expected, retrieved) if e]
    return float(np.mean([e in r[:k] for e, r in pairs])) if pairs else float("nan")


def mrr(expected: list[str], retrieved: list[list[str]]) -> float:
    vals = []
    for e, r in zip(expected, retrieved):
        if not e:
            continue
        vals.append(1 / (r.index(e) + 1) if e in r else 0.0)
    return float(np.mean(vals)) if vals else float("nan")


def key_step_coverage(response: str, steps: list) -> float:
    """Share of expected steps whose keywords appear in the response (any keyword = covered)."""
    if not steps:
        return float("nan")
    text = (response or "").lower()
    covered = sum(any(k.lower() in text for k in kws) for _, kws in steps)
    return covered / len(steps)


def kappa(a, b) -> float:
    return float(cohen_kappa_score(a, b))


def conf_matrix(y, p, labels) -> list[list[int]]:
    return confusion_matrix(y, p, labels=labels).tolist()


def summarise_runs(values: list[float]) -> dict:
    arr = np.array([v for v in values if not (isinstance(v, float) and math.isnan(v))], dtype=float)
    if not len(arr):
        return {"mean": float("nan"), "sd": float("nan"), "runs": values}
    return {"mean": round(float(arr.mean()), 4), "sd": round(float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, 4),
            "runs": [round(float(v), 4) for v in values]}
