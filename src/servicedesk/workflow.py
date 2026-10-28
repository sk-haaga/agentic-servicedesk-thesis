"""Orchestrated agentic workflow (LangGraph state graph) - thesis chapter 4.2.1, Figure 'architecture'.

intake_guard -> create_ticket -> classify -> prioritise -> route -> retrieve -> resolve -> gate
             -> auto_resolve | human_review

Every node writes an audit event. Any exception is recorded and the ticket is referred to a human.
"""
from __future__ import annotations

import sqlite3
import time
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from . import gate as gate_mod
from .agents.classifier import classify
from .agents.resolver import resolve, retrieve
from .config import RUNTIME_DIR, Catalogue, load_catalogue, settings
from .email_intake import Email
from .guard import mask_personal_data, screen_injection
from .itsm.store import Store
from .knowledge import KnowledgeBase
from .llm import SchemaError, get_llm
from .prompts import PROMPT_VERSION
from .rules import compute_priority, route
from .tools import ToolRunner


class TicketState(TypedDict, total=False):
    case_id: str
    correlation: str
    sender: str
    subject: str
    body: str
    text: str
    injection_hits: list[str]
    number: str
    classification: dict
    priority: str
    priority_rules: list[str]
    group: str
    routing_rules: list[str]
    sops: list[dict]
    resolution: dict
    gate: dict
    errors: list[str]
    final_state: str
    review: dict
    blocked_tools: list[str]
    llm_calls: int
    tokens_in: int
    tokens_out: int
    started: float
    latency_s: float


class ServiceDeskWorkflow:
    def __init__(self, llm=None, catalogue: Catalogue | str = "d3", store: Store | None = None, kb: KnowledgeBase | None = None,
                 *, use_rag: bool = True, use_tools: bool = True, triage_only: bool = False, hitl_mode: str | None = None,
                 tau1: float | None = None, tau2: float | None = None, run_id: str | None = None, checkpoint_db=None,
                 defences: bool = True):
        self.llm = llm or get_llm()
        self.catalogue = load_catalogue(catalogue) if isinstance(catalogue, str) else catalogue
        self.store = store or Store()
        self.kb = kb if (kb is not None or triage_only) else KnowledgeBase(self.llm)
        self.use_rag, self.use_tools, self.triage_only = use_rag, use_tools, triage_only
        self.hitl_mode = hitl_mode or settings()["hitl_mode"]
        self.tau1, self.tau2 = tau1, tau2
        # defences=False switches off the injection screen, the prompt-level defences and the gate's injection
        # condition. It exists ONLY for the security experiment (attack success rate without defences).
        self.defences = defences
        self.run_id = run_id or uuid.uuid4().hex[:8]
        checkpointer = None
        if self.hitl_mode == "interrupt":
            from langgraph.checkpoint.sqlite import SqliteSaver
            path = checkpoint_db or RUNTIME_DIR / "checkpoints.db"
            checkpointer = SqliteSaver(sqlite3.connect(path, check_same_thread=False))
        self.graph = self._build().compile(checkpointer=checkpointer)

    # ------------------------------------------------------------------ helpers
    def _audit(self, state, step, *, output=None, res=None, reason=None, confidence=None, input_text=""):
        ticket = state.get("number") or f"pending:{state.get('correlation', '')}"
        self.store.audit(run_id=self.run_id, ticket=ticket, step=step, input_text=input_text, output=output,
                         confidence=confidence, model=getattr(res, "model", None), prompt_version=PROMPT_VERSION,
                         latency_ms=getattr(res, "latency_ms", None), tokens_in=getattr(res, "tokens_in", None),
                         tokens_out=getattr(res, "tokens_out", None), reason=reason)

    @staticmethod
    def _count(state, results) -> dict:
        results = results if isinstance(results, list) else [results]
        return {"llm_calls": state.get("llm_calls", 0) + len(results),
                "tokens_in": state.get("tokens_in", 0) + sum(r.tokens_in for r in results),
                "tokens_out": state.get("tokens_out", 0) + sum(r.tokens_out for r in results)}

    def _failed(self, state) -> bool:
        return bool(state.get("errors"))

    # ------------------------------------------------------------------ nodes
    def intake_guard(self, state: TicketState) -> dict:
        raw = f"Subject: {state.get('subject', '')}\n\n{state.get('body', '')}".strip()
        text = mask_personal_data(raw)
        hits = screen_injection(raw) if self.defences else []
        out = {"text": text, "injection_hits": hits, "errors": [], "started": time.perf_counter(), "llm_calls": 0,
               "tokens_in": 0, "tokens_out": 0, "blocked_tools": []}
        self._audit(state, "intake_guard", output={"injection_hits": hits}, input_text=raw,
                    reason="injection_pattern" if hits else None)
        return out

    def create_ticket(self, state: TicketState) -> dict:
        number = self.store.create_incident({"caller_email": "[masked]" if state.get("sender") else "",
                                             "short_description": state.get("subject", "")[:160],
                                             "description": state["text"], "run_id": self.run_id})
        self.store.relabel_pending(f"pending:{state.get('correlation', '')}", number)
        self._audit({"number": number}, "create_ticket", output={"number": number})
        return {"number": number}

    @staticmethod
    def _err(exc) -> str:
        """Exception class plus the service's error code when present (e.g. BadRequestError:content_filter)."""
        code = getattr(exc, "code", None)
        return f"{type(exc).__name__}:{code}" if code else type(exc).__name__

    def classify(self, state: TicketState) -> dict:
        try:
            res = classify(self.llm, state["text"], self.catalogue, defended=self.defences)
        except SchemaError as exc:
            self._audit(state, "classify", reason=f"schema_error:{exc}"[:200])
            return {"errors": state.get("errors", []) + ["classification_schema"]}
        except Exception as exc:  # API failure after retries
            self._audit(state, "classify", reason=f"llm_error:{self._err(exc)}")
            return {"errors": state.get("errors", []) + [f"classification_{self._err(exc)}"]}
        c = res.parsed.model_dump()
        self._audit(state, "classify", output=c, res=res, confidence=c["confidence"], input_text=state["text"])
        return {"classification": c, **self._count(state, res)}

    def prioritise(self, state: TicketState) -> dict:
        if self._failed(state):
            self._audit(state, "prioritise", reason="skipped:earlier_error")
            return {}
        c = state["classification"]
        priority, rules = compute_priority(c["impact"], c["urgency"], c["category"], self.catalogue)
        self._audit(state, "prioritise", output={"priority": priority, "rules": rules})
        return {"priority": priority, "priority_rules": rules}

    def route(self, state: TicketState) -> dict:
        if self._failed(state):
            self._audit(state, "route", reason="skipped:earlier_error")
            return {}
        c = state["classification"]
        group, rules = route(c["application"], c["category"], self.catalogue)
        self.store.update_incident(state["number"], {"category": c["category"], "cmdb_ci": c["application"], "impact": c["impact"],
                                                     "urgency": c["urgency"], "priority": state["priority"], "assignment_group": group})
        self._audit(state, "route", output={"group": group, "rules": rules})
        return {"group": group, "routing_rules": rules}

    def retrieve(self, state: TicketState) -> dict:
        if self._failed(state) or self.triage_only or not self.use_rag:
            why = "earlier_error" if self._failed(state) else "triage_only" if self.triage_only else "no_rag_condition"
            self._audit(state, "retrieve", reason=f"skipped:{why}")
            return {"sops": []}
        c = state["classification"]
        try:
            hits = retrieve(self.kb, c["summary"], c["application"])
        except Exception as exc:
            self._audit(state, "retrieve", reason=f"retrieval_error:{type(exc).__name__}")
            return {"sops": [], "errors": state.get("errors", []) + ["retrieval"]}
        self._audit(state, "retrieve", output=[(h.sop_id, h.similarity) for h in hits])
        return {"sops": [h.model_dump() for h in hits]}

    def resolve(self, state: TicketState) -> dict:
        if self._failed(state) or self.triage_only:
            self._audit(state, "resolve", reason="skipped:" + ("earlier_error" if self._failed(state) else "triage_only"))
            return {}
        from .schemas import RetrievedSOP
        sops = [RetrievedSOP(**s) for s in state.get("sops", [])]
        runner = ToolRunner(self.kb, lambda step, **kw: self._audit(state, step, **kw))
        try:
            resolution, results = resolve(self.llm, state["text"], _obj(state["classification"]), state["priority"], sops, runner,
                                          use_tools=self.use_tools, norag=not self.use_rag, defended=self.defences)
        except SchemaError as exc:
            self._audit(state, "resolve", reason=f"schema_error:{exc}"[:200])
            return {"errors": state.get("errors", []) + ["resolution_schema"]}
        except Exception as exc:
            self._audit(state, "resolve", reason=f"llm_error:{self._err(exc)}")
            return {"errors": state.get("errors", []) + [f"resolution_{self._err(exc)}"]}
        r = resolution.model_dump()
        if runner.human_requested:
            r["human_requested"] = runner.human_requested
        all_sops = state.get("sops", []) + [s.model_dump() for s in runner.extra_sops]
        self._audit(state, "resolve", output=r, res=results[-1])
        return {"resolution": r, "sops": all_sops, "blocked_tools": runner.blocked, **self._count(state, results)}

    def gate(self, state: TicketState) -> dict:
        c = state.get("classification") or {}
        res = state.get("resolution")
        from .schemas import Resolution
        resolution = Resolution(**{k: v for k, v in res.items() if k in Resolution.model_fields}) if res else None
        top = max([s["similarity"] for s in state.get("sops", [])] or [0.0])
        errors = list(state.get("errors", []))
        if res and res.get("human_requested"):
            errors.append("agent_requested_human")
        if state.get("blocked_tools"):
            errors.append("blocked_tool_call")
        decision = gate_mod.decide(priority=state.get("priority", "P1"), category=c.get("category", ""),
                                   confidence=float(c.get("confidence", 0.0)), top_similarity=top, resolution=resolution,
                                   injection=bool(state.get("injection_hits")) or bool(c.get("injection_suspected")),
                                   errors=errors, catalogue=self.catalogue, tau1=self.tau1, tau2=self.tau2,
                                   disabled=frozenset() if self.defences else frozenset({"injection"}))
        self._audit(state, "gate", output=decision.model_dump(), reason=";".join(decision.reasons))
        return {"gate": decision.model_dump()}

    def auto_resolve(self, state: TicketState) -> dict:
        response = state["resolution"]["response"]
        self.store.update_incident(state["number"], {"state": "Resolved - awaiting user confirmation", "proposed_response": response,
                                                     "resolution_notes": f"Auto-resolved with {', '.join(state['resolution']['sop_ids'])} (sending simulated)",
                                                     "gate_reasons": ";".join(state["gate"]["reasons"])})
        self._audit(state, "auto_resolve", output={"sop_ids": state["resolution"]["sop_ids"]}, reason="email sending simulated")
        return {"final_state": "auto", "latency_s": time.perf_counter() - state.get("started", time.perf_counter())}

    def human_review(self, state: TicketState) -> dict:
        reasons = ";".join(state.get("gate", {}).get("reasons", []))
        proposed = (state.get("resolution") or {}).get("response") or None
        self.store.update_incident(state["number"], {"state": "Awaiting review", "gate_reasons": reasons, "proposed_response": proposed,
                                                     "work_notes": f"Referred to human review: {reasons}"})
        self._audit(state, "human_review_requested", reason=reasons)
        latency = time.perf_counter() - state.get("started", time.perf_counter())
        if self.hitl_mode != "interrupt":
            return {"final_state": "human", "latency_s": latency}
        decision = interrupt({"number": state["number"], "reasons": reasons, "proposed_response": proposed,
                              "classification": state.get("classification"), "priority": state.get("priority"), "group": state.get("group")})
        return {**self.apply_review(state, decision), "latency_s": latency}

    def apply_review(self, state: TicketState, decision: dict) -> dict:
        action = decision.get("action")
        fields: dict[str, Any] = {}
        if action in ("approve", "edit"):
            text = decision.get("response") or state.get("resolution", {}).get("response", "")
            fields = {"state": "Resolved - awaiting user confirmation", "proposed_response": text,
                      "resolution_notes": f"Response {action}d by reviewer {decision.get('reviewer', '')}"}
        elif action == "reassign":
            fields = {"state": "Assigned", "assignment_group": decision.get("group")}
        else:  # reject / escalate
            fields = {"state": "Assigned", "work_notes": f"Rejected by reviewer: {decision.get('comment', '')}"}
        for key in ("priority", "category", "cmdb_ci"):
            if decision.get(key):
                fields[key] = decision[key]
        self.store.update_incident(state["number"], fields)
        self._audit(state, "human_review_decision", output=decision)
        return {"final_state": f"human:{action}", "review": decision}

    # ------------------------------------------------------------------ graph
    def _build(self):
        g = StateGraph(TicketState)
        for name in ("intake_guard", "create_ticket", "classify", "prioritise", "route", "retrieve", "resolve", "gate",
                     "auto_resolve", "human_review"):
            g.add_node(name, getattr(self, name))
        g.add_edge(START, "intake_guard")
        for a, b in (("intake_guard", "create_ticket"), ("create_ticket", "classify"), ("classify", "prioritise"),
                     ("prioritise", "route"), ("route", "retrieve"), ("retrieve", "resolve"), ("resolve", "gate")):
            g.add_edge(a, b)
        g.add_conditional_edges("gate", lambda s: "auto_resolve" if s["gate"]["route"] == "auto" else "human_review",
                                {"auto_resolve": "auto_resolve", "human_review": "human_review"})
        g.add_edge("auto_resolve", END)
        g.add_edge("human_review", END)
        return g

    # ------------------------------------------------------------------ public API
    def process(self, email: Email, case_id: str = "", thread_id: str | None = None) -> TicketState:
        cfg = {"configurable": {"thread_id": thread_id or uuid.uuid4().hex}}
        return self.graph.invoke({"case_id": case_id, "correlation": uuid.uuid4().hex, "sender": email.sender,
                                  "subject": email.subject, "body": email.body}, cfg)

    def resume(self, thread_id: str, decision: dict) -> TicketState:
        return self.graph.invoke(Command(resume=decision), {"configurable": {"thread_id": thread_id}})


class _obj:
    """Attribute access for dicts (classification passed to the resolver)."""

    def __init__(self, d: dict):
        self.__dict__.update(d)
