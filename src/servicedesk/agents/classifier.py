"""Classifier agent: category, application, impact, urgency, evidence and confidence (structured output)."""
from __future__ import annotations

from ..config import Catalogue
from ..guard import delimit
from ..prompts import CLASSIFIER_SYSTEM, CLASSIFIER_SYSTEM_D1, CLASSIFIER_SYSTEM_UNDEFENDED, CLASSIFIER_USER
from ..schemas import classification_model


def classify(llm, text: str, catalogue: Catalogue, defended: bool = True):
    """defended=False removes the prompt-level defences (security experiment only)."""
    schema = classification_model(catalogue)
    if not defended:
        template = CLASSIFIER_SYSTEM_UNDEFENDED
    else:
        template = CLASSIFIER_SYSTEM_D1 if catalogue.name == "d1" else CLASSIFIER_SYSTEM
    system = template.format(catalogue=catalogue.describe())
    user = CLASSIFIER_USER.format(ticket=delimit(text) if defended else text)
    res = llm.parse(system, user, schema, context={"text": text, "catalogue": catalogue})
    res.parsed.confidence = min(1.0, max(0.0, float(res.parsed.confidence)))  # range enforced in code (strict schemas reject min/max)
    return res
