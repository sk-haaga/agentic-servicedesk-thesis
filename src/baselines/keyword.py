"""Keyword baseline (B0): fixed keyword and alias rules from the service catalogue.

It uses the same priority matrix and routing rules as the prototype, so a comparison isolates the
contribution of the LLM to interpreting the email."""
from __future__ import annotations

import re

from ..servicedesk.config import Catalogue


def _hits(text: str, keywords: list[str]) -> list[str]:
    found = []
    for kw in keywords:
        if re.search(r"(?<![\w])" + re.escape(kw.lower()) + r"(?![\w])", text):
            found.append(kw)
    return found


def _best(text: str, items: list[dict]) -> tuple[str, list[str]]:
    scored = [(len(_hits(text, it.get("keywords", []))), i, it) for i, it in enumerate(items)]
    scored.sort(key=lambda x: (-x[0], x[1]))
    n, _, best = scored[0]
    return best["name"], (_hits(text, best.get("keywords", [])) if n else [])


def classify(text: str, catalogue: Catalogue) -> dict:
    t = text.lower()
    category, cat_ev = _best(t, catalogue.categories)
    application, app_ev = _best(t, catalogue.applications)
    imp_high = _hits(t, catalogue.impact_keywords.get("high", []))
    imp_med = _hits(t, catalogue.impact_keywords.get("medium", []))
    impact = "high" if imp_high else "medium" if imp_med else "low"
    urg_high = _hits(t, catalogue.urgency_keywords.get("high", []))
    urg_low = _hits(t, catalogue.urgency_keywords.get("low", []))
    urgency = "high" if urg_high else "low" if urg_low else "medium"
    evidence = (cat_ev + app_ev + imp_high + imp_med + urg_high + urg_low)[:6]
    confidence = 0.9 if (cat_ev and app_ev) else 0.6 if (cat_ev or app_ev) else 0.3
    first = text.strip().splitlines()[0] if text.strip() else ""
    return {"summary": first[:150], "category": category, "application": application, "impact": impact,
            "urgency": urgency, "evidence": evidence, "confidence": confidence}
