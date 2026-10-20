"""Classifier agent: category, application, impact, urgency, evidence and confidence (structured output)."""
from __future__ import annotations

from ..config import Catalogue
from ..guard import delimit
from ..prompts import CLASSIFIER_SYSTEM, CLASSIFIER_SYSTEM_D1, CLASSIFIER_USER
from ..schemas import classification_model


def classify(llm, text: str, catalogue: Catalogue):
    schema = classification_model(catalogue)
    template = CLASSIFIER_SYSTEM_D1 if catalogue.name == "d1" else CLASSIFIER_SYSTEM
    system = template.format(catalogue=catalogue.describe())
    user = CLASSIFIER_USER.format(ticket=delimit(text))
    res = llm.parse(system, user, schema, context={"text": text, "catalogue": catalogue})
    res.parsed.confidence = min(1.0, max(0.0, float(res.parsed.confidence)))  # range enforced in code (strict schemas reject min/max)
    return res
