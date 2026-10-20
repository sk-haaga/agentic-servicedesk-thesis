"""Deterministic business rules: priority matrix and routing (no LLM involved)."""
from __future__ import annotations

from .config import Catalogue

# Impact x urgency -> priority (thesis chapter 4.2.2). P1 = high, P2 = medium, P3 = low.
PRIORITY_MATRIX: dict[tuple[str, str], str] = {
    ("high", "high"): "P1", ("high", "medium"): "P1", ("high", "low"): "P2",
    ("medium", "high"): "P1", ("medium", "medium"): "P2", ("medium", "low"): "P3",
    ("low", "high"): "P2", ("low", "medium"): "P3", ("low", "low"): "P3",
}


def compute_priority(impact: str, urgency: str, category: str | None, catalogue: Catalogue) -> tuple[str, list[str]]:
    """Return (priority, applied_rules)."""
    rules = [f"matrix({impact},{urgency})"]
    priority = PRIORITY_MATRIX[(impact, urgency)]
    if catalogue.security_category and category == catalogue.security_category and priority != "P1":
        priority = "P1"
        rules.append("override:security->P1")
    return priority, rules


def route(application: str, category: str | None, catalogue: Catalogue) -> tuple[str, list[str]]:
    """Return (resolver group, applied_rules)."""
    if catalogue.security_category and category == catalogue.security_category:
        return catalogue.security_group, ["override:security->Security Operations"]
    group = catalogue.group_for(application)
    if group is None:
        return "Service Desk L1", ["fallback:unknown application"]
    return group, [f"catalogue({application})"]
