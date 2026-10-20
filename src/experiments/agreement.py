"""Agreement between the author's blind groundedness scores and the LLM judge (experiment E4).

1. Open results/<provider>/e4_blind_scoring_sheet.csv, fill the 'author_score' column (0, 1 or 2)
   using the rubric in thesis Appendix 6, without looking at e4_blind_key.csv.
2. python -m src.experiments.agreement --provider azure
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from ..servicedesk.config import ROOT
from .metrics import kappa


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="azure")
    a = ap.parse_args(argv)
    out = ROOT / "results" / a.provider
    sheet = pd.read_csv(out / "e4_blind_scoring_sheet.csv")
    key = pd.read_csv(out / "e4_blind_key.csv")
    df = sheet[["item", "author_score"]].merge(key[["item", "condition", "llm_score"]], on="item").dropna(subset=["author_score", "llm_score"])
    df["author_score"] = df["author_score"].astype(int)
    df["llm_score"] = df["llm_score"].astype(int)
    res = {"n": len(df), "exact_agreement": round(float((df["author_score"] == df["llm_score"]).mean()), 4),
           "cohen_kappa": round(kappa(df["author_score"], df["llm_score"]), 4),
           "author_share_2_1_0_by_condition": {c: [round(float((g["author_score"] == k).mean()), 4) for k in (2, 1, 0)] for c, g in df.groupby("condition")}}
    (out / "e4_agreement.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
