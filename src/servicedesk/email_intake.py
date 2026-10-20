"""Email intake: parse .eml files or raw text into subject, sender and body."""
from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser, Parser
from pathlib import Path


@dataclass
class Email:
    sender: str
    subject: str
    body: str

    @property
    def text(self) -> str:
        return f"Subject: {self.subject}\n\n{self.body}".strip()


def _body(msg) -> str:
    part = msg.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    content = part.get_content()
    if part.get_content_type() == "text/html":
        import re
        content = re.sub(r"<[^>]+>", " ", content)
    return content.strip()


def parse_eml(path: str | Path) -> Email:
    with open(path, "rb") as fh:
        msg = BytesParser(policy=policy.default).parse(fh)
    return Email(sender=str(msg.get("From", "")), subject=str(msg.get("Subject", "")), body=_body(msg))


def parse_raw(raw: str) -> Email:
    """Parse an email given as text (with or without headers)."""
    if raw.lstrip().lower().startswith(("from:", "subject:", "to:")):
        msg = Parser(policy=policy.default).parsestr(raw)
        return Email(sender=str(msg.get("From", "")), subject=str(msg.get("Subject", "")), body=_body(msg) or msg.get_payload())
    return Email(sender="", subject="", body=raw.strip())


def from_fields(subject, body, sender: str = "") -> Email:
    """Build an Email from dataset fields; missing values (None/NaN) become empty strings."""
    clean = lambda v: v.strip() if isinstance(v, str) else ""
    return Email(sender=sender, subject=clean(subject), body=clean(body))
