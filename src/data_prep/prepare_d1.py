"""Prepare the public ticket dataset D1 (Bueck 2025, CC BY-NC 4.0) - thesis chapter 3.3.4 and Appendix 4.

Steps: English only -> IT-related queues -> drop exact duplicates and empty bodies -> map priority to P1-P3
-> group near-duplicate tickets (TF-IDF cosine >= 0.8; the generated dataset contains many paraphrased
variants) -> group-aware split into test (400), development (100) and training pool (rest), so that no
near-duplicate group appears in more than one split (prevents leakage, Kaufman et al. 2012). Test and
development sets contain one ticket per group. The split is deterministic (seed 42).

    python -m src.data_prep.prepare_d1
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer

from ..servicedesk.config import ROOT

RAW = ROOT / "data" / "raw" / "aa_dataset-tickets-multi-lang-5-2-50-version.csv"
OUT = ROOT / "data" / "processed"
IT_QUEUES = ["Technical Support", "Product Support", "IT Support", "Service Outages and Maintenance"]
PRIORITY_MAP = {"high": "P1", "medium": "P2", "low": "P3"}
SEED, N_TEST, N_DEV, SIM = 42, 400, 100, 0.8


def near_duplicate_groups(texts: list[str], threshold: float) -> np.ndarray:
    """Connected components of the graph linking texts with TF-IDF cosine similarity >= threshold."""
    X = TfidfVectorizer(sublinear_tf=True).fit_transform(texts)
    rows, cols = [], []
    for start in range(0, X.shape[0], 2000):
        sim = (X[start:start + 2000] @ X.T).tocoo()
        mask = sim.data >= threshold
        rows.append(sim.row[mask] + start)
        cols.append(sim.col[mask])
    from scipy.sparse import coo_matrix
    r, c = np.concatenate(rows), np.concatenate(cols)
    graph = coo_matrix((np.ones(len(r)), (r, c)), shape=(X.shape[0], X.shape[0]))
    _, labels = connected_components(graph, directed=False)
    return labels


def main(raw: Path = RAW) -> dict:
    df = pd.read_csv(raw)
    df.insert(0, "row_id", df.index)  # identifier in the original file
    log = {"source_rows": len(df)}
    df = df[df["language"] == "en"]; log["english"] = len(df)
    df = df[df["queue"].isin(IT_QUEUES)]; log["it_queues"] = len(df)
    df = df[df["body"].fillna("").str.strip().str.len() > 0]
    df = df.drop_duplicates(subset=["subject", "body"]); log["after_cleaning"] = len(df)
    df["priority_p"] = df["priority"].map(PRIORITY_MAP)
    df = df.dropna(subset=["priority_p"])
    df = df.reset_index(drop=True)
    groups = near_duplicate_groups((df["subject"].fillna("") + " " + df["body"]).tolist(), SIM)
    df["dup_group"] = groups
    log["near_duplicate_groups"] = int(groups.max() + 1)
    log["tickets_in_groups_of_2_or_more"] = int((df.groupby("dup_group")["row_id"].transform("size") > 1).sum())
    # one representative per group is eligible for test/dev; stratify by queue x priority
    rng = np.random.default_rng(SEED)
    reps = df.sample(frac=1, random_state=SEED).drop_duplicates("dup_group")
    reps = reps.assign(stratum=reps["queue"] + "|" + reps["priority_p"])
    share = df.assign(stratum=df["queue"] + "|" + df["priority_p"])["stratum"].value_counts(normalize=True)
    def take(pool, n):
        picked = []
        for stratum, frac in share.items():
            k = int(round(frac * n))
            cand = pool[pool["stratum"] == stratum]
            picked.append(cand.head(k))
        out = pd.concat(picked)
        if len(out) < n:
            out = pd.concat([out, pool.drop(out.index).head(n - len(out))])
        return out.head(n)
    test = take(reps, N_TEST)
    dev = take(reps.drop(test.index), N_DEV)
    used = set(test["dup_group"]) | set(dev["dup_group"])
    train = df[~df["dup_group"].isin(used)]
    OUT.mkdir(parents=True, exist_ok=True)
    cols = ["row_id", "subject", "body", "answer", "type", "queue", "priority", "priority_p"]
    for name, part in (("train", train), ("dev", dev), ("test", test)):
        part[cols].to_csv(OUT / f"d1_{name}.csv", index=False)
        (OUT / f"d1_{name}_ids.txt").write_text("\n".join(map(str, sorted(part["row_id"]))))
    log.update({"train": len(train), "dev": len(dev), "test": len(test),
                "queue_distribution": df["queue"].value_counts().to_dict(),
                "priority_distribution": df["priority_p"].value_counts().sort_index().to_dict(),
                "test_priority_distribution": test["priority_p"].value_counts().sort_index().to_dict()})
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "d1_preparation.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))
    return log


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else RAW)
