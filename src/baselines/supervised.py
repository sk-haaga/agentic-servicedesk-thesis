"""Supervised baseline (B1): TF-IDF + logistic regression trained on the D1 training pool.

Represents the conventional approach that needs labelled historical tickets (Revina et al. 2020)."""
from __future__ import annotations

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline


def make_pipeline() -> Pipeline:
    return Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_df=0.9, sublinear_tf=True, strip_accents="unicode")),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced", C=4.0)),
    ])


class SupervisedBaseline:
    def __init__(self):
        self.models: dict[str, Pipeline] = {}

    def fit(self, train: pd.DataFrame, targets=("queue", "priority_p")) -> "SupervisedBaseline":
        text = (train["subject"].fillna("") + "\n" + train["body"].fillna("")).tolist()
        for t in targets:
            self.models[t] = make_pipeline().fit(text, train[t].tolist())
        return self

    def predict(self, df: pd.DataFrame) -> pd.DataFrame:
        text = (df["subject"].fillna("") + "\n" + df["body"].fillna("")).tolist()
        return pd.DataFrame({t: m.predict(text) for t, m in self.models.items()}, index=df.index)
