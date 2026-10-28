"""Command-line demo: process one or more .eml files and print the triage result.

    python -m src.servicedesk.cli data/d3/emails/C01-1.eml data/d3/emails/C11-1.eml
"""
from __future__ import annotations

import json
import sys

from .email_intake import parse_eml
from .workflow import ServiceDeskWorkflow


def main(paths: list[str]) -> None:
    wf = ServiceDeskWorkflow(catalogue="d3")
    for p in paths:
        st = wf.process(parse_eml(p))
        c = st.get("classification") or {}
        print(json.dumps({"file": p, "ticket": st.get("number"), "category": c.get("category"), "application": c.get("application"),
                          "impact": c.get("impact"), "urgency": c.get("urgency"), "priority": st.get("priority"), "group": st.get("group"),
                          "confidence": c.get("confidence"), "sops": [s["sop_id"] for s in st.get("sops", [])][:3],
                          "route": st.get("final_state"), "reasons": (st.get("gate") or {}).get("reasons"),
                          "response": (st.get("resolution") or {}).get("response", "")[:400]}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:] or ["data/d3/emails/C01-1.eml"])
