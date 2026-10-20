"""Tool allow-list (thesis chapter 4.2.4). Only these tools exist; any other tool name requested by a
model is refused and logged as a blocked action. No tool can change systems other than the ticket."""
from __future__ import annotations

import json

ALLOWED_TOOLS = {"create_ticket", "update_ticket", "lookup_service_catalogue", "search_sops", "request_human_review"}

# Tools exposed to the resolver agent through function calling (subset of the allow-list).
RESOLVER_TOOL_SPECS = [
    {"type": "function", "function": {
        "name": "search_sops",
        "description": "Search the SOP knowledge base with a new query. Returns the top SOPs.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"], "additionalProperties": False}}},
    {"type": "function", "function": {
        "name": "request_human_review",
        "description": "Refer the ticket to a human reviewer with a short reason.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string"}}, "required": ["reason"], "additionalProperties": False}}},
]


class ToolRunner:
    """Executes tool calls requested by an agent, enforcing the allow-list."""

    def __init__(self, kb, audit, allowed: set[str] | None = None):
        self.kb = kb
        self.audit = audit
        self.allowed = allowed or {"search_sops", "request_human_review"}
        self.blocked: list[str] = []
        self.human_requested: str | None = None
        self.extra_sops = []

    def run(self, name: str, arguments: str) -> str:
        if name not in ALLOWED_TOOLS or name not in self.allowed:
            self.blocked.append(name)
            self.audit("tool_blocked", output={"tool": name, "arguments": arguments[:200]}, reason="not in allow-list")
            return json.dumps({"error": f"tool '{name}' is not allowed"})
        try:
            args = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return json.dumps({"error": "invalid arguments"})
        if name == "search_sops":
            hits = self.kb.search(str(args.get("query", ""))[:300])
            self.extra_sops.extend(hits)
            self.audit("tool_search_sops", output={"query": args.get("query"), "hits": [(h.sop_id, h.similarity) for h in hits]})
            return json.dumps([{"sop_id": h.sop_id, "similarity": h.similarity, "text": h.text} for h in hits])
        if name == "request_human_review":
            self.human_requested = str(args.get("reason", ""))[:200]
            self.audit("tool_request_human_review", output=args)
            return json.dumps({"status": "noted"})
        return json.dumps({"error": "not available to this agent"})
