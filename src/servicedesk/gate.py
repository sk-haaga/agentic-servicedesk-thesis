"""Confidence and policy gate (thesis chapter 4.2.3). A response is auto-eligible only if ALL
conditions hold; every failed condition is recorded as a reason code.

`disabled` switches individual conditions off. It is used only by the guardrail ablation of the
experiment runner (re-applied offline to stored outputs); the prototype itself always uses all conditions.
"""
from __future__ import annotations

from .config import Catalogue, settings
from .schemas import GateDecision

# Names of the gate conditions that the ablation can switch off.
CONDITIONS = ("errors", "injection", "priority_policy", "category_policy", "confidence", "similarity", "grounded")


def decide(*, priority: str, category: str, confidence: float, top_similarity: float, resolution,
           injection: bool, errors: list[str], catalogue: Catalogue, tau1: float | None = None,
           tau2: float | None = None, disabled: frozenset | set = frozenset()) -> GateDecision:
    g = settings()["gate"]
    tau1 = g["tau_confidence"] if tau1 is None else tau1
    tau2 = g["tau_similarity"] if tau2 is None else tau2
    unknown = set(disabled) - set(CONDITIONS)
    if unknown:
        raise ValueError(f"unknown gate conditions: {sorted(unknown)}")
    on = lambda name: name not in disabled  # noqa: E731
    reasons = []
    if errors and on("errors"):
        reasons += [f"error:{e}" for e in errors]
    if injection and on("injection"):
        reasons.append("injection_suspected")
    if priority not in g["auto_priorities"] and on("priority_policy"):
        reasons.append(f"priority_{priority}_requires_human")
    if on("category_policy"):
        if catalogue.security_category and category == catalogue.security_category:
            reasons.append("security_incident")
        if category not in catalogue.auto_categories:
            reasons.append("category_not_auto_eligible")
    if confidence < tau1 and on("confidence"):
        reasons.append(f"confidence_below_{tau1}")
    if top_similarity < tau2 and on("similarity"):
        reasons.append(f"sop_similarity_below_{tau2}")
    if on("grounded"):
        if resolution is None or not resolution.answerable or not resolution.sop_ids:
            reasons.append("no_grounded_answer")
        elif resolution.self_check != "covered":
            reasons.append(f"self_check_{resolution.self_check}")
    return GateDecision(route="human" if reasons else "auto", reasons=reasons or ["all_conditions_met"])
