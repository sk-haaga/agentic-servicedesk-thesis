"""Confidence and policy gate (thesis chapter 4.2.3). A response is auto-eligible only if ALL
conditions hold; every failed condition is recorded as a reason code."""
from __future__ import annotations

from .config import Catalogue, settings
from .schemas import GateDecision


def decide(*, priority: str, category: str, confidence: float, top_similarity: float, resolution,
           injection: bool, errors: list[str], catalogue: Catalogue, tau1: float | None = None,
           tau2: float | None = None) -> GateDecision:
    g = settings()["gate"]
    tau1 = g["tau_confidence"] if tau1 is None else tau1
    tau2 = g["tau_similarity"] if tau2 is None else tau2
    reasons = []
    if errors:
        reasons += [f"error:{e}" for e in errors]
    if injection:
        reasons.append("injection_suspected")
    if priority not in g["auto_priorities"]:
        reasons.append(f"priority_{priority}_requires_human")
    if catalogue.security_category and category == catalogue.security_category:
        reasons.append("security_incident")
    if category not in catalogue.auto_categories:
        reasons.append("category_not_auto_eligible")
    if confidence < tau1:
        reasons.append(f"confidence_below_{tau1}")
    if top_similarity < tau2:
        reasons.append(f"sop_similarity_below_{tau2}")
    if resolution is None or not resolution.answerable or not resolution.sop_ids:
        reasons.append("no_grounded_answer")
    elif resolution.self_check != "covered":
        reasons.append(f"self_check_{resolution.self_check}")
    return GateDecision(route="human" if reasons else "auto", reasons=reasons or ["all_conditions_met"])
