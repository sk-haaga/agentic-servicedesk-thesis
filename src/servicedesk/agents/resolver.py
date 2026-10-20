"""Knowledge and resolver agents.

The knowledge agent retrieves SOPs with the classifier's summary as query. The resolver agent may call
two allow-listed tools (search_sops, request_human_review) for at most `max_tool_steps` steps, and
then returns a structured Resolution that cites the SOPs it used, or abstains."""
from __future__ import annotations

import json

from ..config import settings
from ..guard import delimit
from ..prompts import RESOLVER_SYSTEM, RESOLVER_SYSTEM_NORAG, RESOLVER_USER
from ..schemas import Resolution
from ..tools import RESOLVER_TOOL_SPECS


def retrieve(kb, summary: str, application: str, k: int | None = None):
    query = f"{application}: {summary}"
    return kb.search(query, k or settings()["retrieval_top_k"])


def format_sops(sops) -> str:
    if not sops:
        return "(none)"
    return "\n\n".join(f"[{s.sop_id}] (similarity {s.similarity:.2f})\n{s.text}" for s in sops)


def resolve(llm, ticket_text: str, classification, priority: str, sops, runner, use_tools: bool = True, norag: bool = False):
    """Return (Resolution, list_of_llm_results)."""
    user = RESOLVER_USER.format(category=classification.category, application=classification.application,
                                priority=priority, ticket=delimit(ticket_text), sops=format_sops(sops))
    system = RESOLVER_SYSTEM_NORAG if norag else RESOLVER_SYSTEM
    if norag:
        user = user.split("Retrieved SOPs:")[0].strip()
    messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    results = []
    if use_tools and not norag and not llm.is_fake:
        for _ in range(int(settings()["max_tool_steps"])):
            msg, res = llm.chat_tools(messages, RESOLVER_TOOL_SPECS)
            results.append(res)
            calls = getattr(msg, "tool_calls", None)
            if not calls:
                break
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [{"id": c.id, "type": "function",
                                             "function": {"name": c.function.name, "arguments": c.function.arguments}} for c in calls]})
            for c in calls:
                messages.append({"role": "tool", "tool_call_id": c.id, "content": runner.run(c.function.name, c.function.arguments)})
        messages.append({"role": "user", "content": "Now give your final answer in the required format."})
    final = llm.parse(system, user, Resolution, context={"sops": sops + runner.extra_sops}, messages=messages)
    results.append(final)
    resolution: Resolution = final.parsed
    # consistency rules: citations must refer to SOPs that were actually retrieved
    if norag:
        resolution.sop_ids = []
        return resolution, results
    known = {s.sop_id for s in sops} | {s.sop_id for s in runner.extra_sops}
    resolution.sop_ids = [i for i in resolution.sop_ids if i in known]
    if resolution.answerable and not resolution.sop_ids:
        resolution.answerable = False
        resolution.self_check = "not_covered"
    return resolution, results
