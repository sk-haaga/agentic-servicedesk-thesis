"""Agreement between the author's blind groundedness scores and the LLM judge (experiment E4).

1. Open <results folder>/e4_blind_scoring_sheet.csv and fill the 'author_score' column (0, 1 or 2)
   with the rubric in thesis Appendix 6, without looking at e4_blind_key.csv.
2. python -m src.experiments.agreement --folder results/azure_YYYY-MM-DD-HH-MM

Reports exact agreement, Cohen's kappa and linearly weighted kappa (the scores are ordinal).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from ..servicedesk.config import ROOT


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", required=True, help="results folder, e.g. results/azure_2026-11-02-10-15")
    a = ap.parse_args(argv)
    out = Path(a.folder)
    out = out if out.is_absolute() else ROOT / out
    sheet = pd.read_csv(out / "e4_blind_scoring_sheet.csv")
    key = pd.read_csv(out / "e4_blind_key.csv")
    df = sheet[["item", "author_score"]].merge(key[["item", "condition", "llm_score"]], on="item").dropna(subset=["author_score", "llm_score"])
    df["author_score"] = df["author_score"].astype(int)
    df["llm_score"] = df["llm_score"].astype(int)
    res = {"n": len(df), "exact_agreement": round(float((df["author_score"] == df["llm_score"]).mean()), 4),
           "cohen_kappa": round(float(cohen_kappa_score(df["author_score"], df["llm_score"])), 4),
           "weighted_kappa_linear": round(float(cohen_kappa_score(df["author_score"], df["llm_score"], weights="linear")), 4),
           "author_share_2_1_0_by_condition": {c: [round(float((g["author_score"] == k).mean()), 4) for k in (2, 1, 0)] for c, g in df.groupby("condition")},
           "llm_share_2_1_0_by_condition": {c: [round(float((g["llm_score"] == k).mean()), 4) for k in (2, 1, 0)] for c, g in df.groupby("condition")}}
    (out / "e4_agreement.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
