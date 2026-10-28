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


# ----------------------------------------------------------------------------- design iteration 2
def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact (Clopper-Pearson) confidence interval for a proportion k/n (Clopper & Pearson 1934)."""
    from scipy.stats import beta
    if n <= 0:
        return (float("nan"), float("nan"))
    lo = 0.0 if k <= 0 else float(beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k >= n else float(beta.ppf(1 - alpha / 2, k + 1, n - k))
    return (round(lo, 4), round(hi, 4))


def sign_test(better: int, worse: int) -> float:
    """Two-sided exact sign test (ties excluded)."""
    n = better + worse
    if n == 0:
        return 1.0
    k = min(better, worse)
    return min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)


def cluster_bootstrap(df, cluster: str, cols: list[str], n: int = 5000, seed: int = 42, diff: tuple[str, str] | None = None) -> dict:
    """Percentile bootstrap that resamples whole clusters (e.g. scenario cards whose paraphrases are not
    independent). `df` has one row per observation (email x run) with 0/1 or numeric columns `cols`.
    Returns the mean and a 95 % interval for every column and, if `diff` is given, for mean(a) - mean(b)."""
    rng = np.random.default_rng(seed)
    sums = df.groupby(cluster)[cols].sum()
    counts = df.groupby(cluster).size()
    keys = sums.index.to_numpy()
    S, C = sums.to_numpy(dtype=float), counts.to_numpy(dtype=float)
    idx = rng.integers(0, len(keys), size=(n, len(keys)))
    boot = S[idx].sum(axis=1) / C[idx].sum(axis=1)[:, None]          # n x len(cols)
    point = S.sum(axis=0) / C.sum()
    out = {c: {"mean": round(float(point[j]), 4), "ci": [round(float(np.percentile(boot[:, j], 2.5)), 4),
                                                         round(float(np.percentile(boot[:, j], 97.5)), 4)]}
           for j, c in enumerate(cols)}
    if diff:
        a, b = cols.index(diff[0]), cols.index(diff[1])
        d = boot[:, a] - boot[:, b]
        out["difference"] = {"of": list(diff), "mean": round(float(point[a] - point[b]), 4),
                             "ci": [round(float(np.percentile(d, 2.5)), 4), round(float(np.percentile(d, 97.5)), 4)]}
    out["clusters"] = int(len(keys))
    return out


def fleiss_kappa(labels: list[list]) -> float:
    """Fleiss' kappa for items (rows) rated by the same number of raters (columns); here: the repeated runs
    of the prototype are the raters (Fleiss 1971)."""
    rows = [list(r) for r in labels if len(r) > 1]
    if not rows:
        return float("nan")
    m = len(rows[0])
    cats = sorted({str(x) for r in rows for x in r})
    if len(cats) == 1:
        return 1.0
    counts = np.array([[sum(str(x) == c for x in r) for c in cats] for r in rows], dtype=float)
    p_i = ((counts ** 2).sum(axis=1) - m) / (m * (m - 1))
    p_j = counts.sum(axis=0) / (len(rows) * m)
    pe = float((p_j ** 2).sum())
    return float((p_i.mean() - pe) / (1 - pe)) if pe < 1 else 1.0


def consistency(frames: list, field: str, gold: dict | None = None) -> dict:
    """Agreement of one output field across repeated runs (experiment E8).
    frames: one DataFrame per run with columns 'id' and `field`; gold: optional id -> correct value."""
    import pandas as pd
    wide = pd.concat([f.set_index("id")[field].rename(i) for i, f in enumerate(frames)], axis=1)
    wide = wide.map(lambda x: "none" if x is None or (isinstance(x, float) and math.isnan(x)) else str(x))
    rows = wide.values.tolist()
    modal_share = [max(r.count(v) for v in set(r)) / len(r) for r in rows]
    unanimous = [len(set(r)) == 1 for r in rows]
    res = {"items": len(rows), "runs": len(frames), "unanimous_share": round(float(np.mean(unanimous)), 4),
           "items_changed_at_least_once": int(len(rows) - sum(unanimous)),
           "mean_agreement_with_majority": round(float(np.mean(modal_share)), 4),
           "fleiss_kappa": round(fleiss_kappa(rows), 4) if len(frames) > 1 else None}
    if gold is not None:
        ids = list(wide.index)
        majority = [max(sorted(set(r)), key=r.count) for r in rows]  # ties: alphabetical, deterministic
        res["majority_vote_accuracy"] = round(float(np.mean([m == str(gold[i]) for m, i in zip(majority, ids)])), 4)
        res["mean_run_accuracy"] = round(float(np.mean([[v == str(gold[i]) for v in r] for r, i in zip(rows, ids)])), 4)
    return res
