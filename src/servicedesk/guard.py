"""Intake guard: personal-data masking, untrusted-input delimiting and prompt-injection screening."""
from __future__ import annotations

import re

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)+")
PHONE_RE = re.compile(r"(?<!\w)(\+?\d[\d\s().-]{7,}\d)(?!\w)")

# Heuristic patterns for instructions aimed at the AI rather than the service desk.
INJECTION_PATTERNS = [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|rules|prompts?)",
    r"disregard (all |any |the )?(previous|prior|above|your) (instructions|rules)",
    r"forget (all |your )?(previous )?(instructions|rules)",
    r"\b(system|assistant|developer)\s*(prompt|message)?\s*:",
    r"you are now\b",
    r"new instructions?\b",
    r"\b(set|mark|change|classify)\b[^.\n]{0,40}\b(priority|ticket)\b[^.\n]{0,25}\b(p[1-3]|high|low|critical)\b",
    r"\b(route|assign|send)\b[^.\n]{0,30}\b(this|the) ticket\b[^.\n]{0,30}\bto\b",
    r"\b(reveal|show|send|give|print)\b[^.\n]{0,30}\b(password|credentials?|api key|secret|system prompt)\b",
    r"\b(execute|run)\b[^.\n]{0,20}\b(command|script|tool|reset tool|shell|powershell)\b",
    r"</?ticket>",
    r"\bauto[- ]?(resolve|close|approve)\b",
]
INJECTION_RE = re.compile("|".join(f"(?:{p})" for p in INJECTION_PATTERNS), re.IGNORECASE)


def mask_personal_data(text: str) -> str:
    text = EMAIL_RE.sub("[EMAIL]", text)
    return PHONE_RE.sub("[PHONE]", text)


def screen_injection(text: str) -> list[str]:
    """Return the suspicious fragments found (empty list = nothing found)."""
    return [m.group(0)[:80] for m in INJECTION_RE.finditer(text)]


def delimit(text: str) -> str:
    """Wrap untrusted text in tags; neutralise any tags inside it (spotlighting)."""
    safe = re.sub(r"</?\s*ticket\s*>", "[tag removed]", text, flags=re.IGNORECASE)
    return f"<ticket>\n{safe}\n</ticket>"
