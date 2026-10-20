"""Human-in-the-loop review console (Streamlit) - thesis chapter 4.2.5.

    streamlit run src/servicedesk/console.py

Two pages: 'Inbox' submits an email to the workflow (interrupt mode: the graph pauses when human review
is needed); 'Review queue' shows paused tickets with the agent's proposal, evidence, confidence, priority
rule and cited SOP, and resumes the graph with the reviewer's decision (approve / edit / reject / reassign).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import streamlit as st  # noqa: E402

from src.servicedesk.config import load_catalogue  # noqa: E402
from src.servicedesk.email_intake import from_fields, parse_eml  # noqa: E402
from src.servicedesk.itsm.store import Store  # noqa: E402
from src.servicedesk.workflow import ServiceDeskWorkflow  # noqa: E402

st.set_page_config(page_title="Agentic Service Desk – Review Console", layout="wide")


@st.cache_resource
def workflow():
    return ServiceDeskWorkflow(catalogue="d2", hitl_mode="interrupt")


wf = workflow()
store: Store = wf.store
catalogue = load_catalogue("d2")
page = st.sidebar.radio("Page", ["Inbox", "Review queue", "All tickets"])
st.sidebar.caption(f"LLM: {wf.llm.name} · model: {wf.llm.chat_model}")

if page == "Inbox":
    st.header("Inbox – submit a user email")
    samples = sorted((Path(__file__).resolve().parents[2] / "data" / "d2" / "emails").glob("*.eml"))
    pick = st.selectbox("Load a benchmark email (optional)", ["—"] + [p.stem for p in samples])
    subject, body = "", ""
    if pick != "—":
        e = parse_eml(next(p for p in samples if p.stem == pick))
        subject, body = e.subject, e.body
    subject = st.text_input("Subject", subject)
    body = st.text_area("Body", body, height=180)
    if st.button("Process email", type="primary") and (subject or body):
        with st.spinner("Running the agentic workflow…"):
            thread = f"T-{abs(hash(subject + body)) % 10**8}"
            out = wf.process(from_fields(subject, body), thread_id=thread)
        if "__interrupt__" in out:
            st.warning(f"{out['number']}: referred to human review – {out['__interrupt__'][0].value['reasons']}")
            store.update_incident(out["number"], {"work_notes": f"thread:{thread}"})
        else:
            st.success(f"{out['number']}: auto-eligible response stored (sending simulated)")
        st.json({k: out.get(k) for k in ("number", "classification", "priority", "group", "gate", "resolution")})

elif page == "Review queue":
    st.header("Review queue")
    queue = store.list_incidents("Awaiting review")
    if not queue:
        st.info("No tickets are waiting for review.")
    for inc in queue:
        with st.expander(f"{inc['number']} · {inc['priority']} · {inc['short_description']}", expanded=False):
            c1, c2 = st.columns([3, 2])
            c1.markdown("**Email (personal data masked)**")
            c1.text(inc["description"])
            c1.markdown("**Proposed response**")
            proposed = c1.text_area("Edit before approving", inc.get("proposed_response") or "", key=f"r{inc['number']}", height=150)
            events = store.audit_events(inc["number"])
            cls = next((json.loads(e["output"]) for e in events if e["step"] == "classify" and e["output"]), {})
            prio = next((json.loads(e["output"]) for e in events if e["step"] == "prioritise" and e["output"]), {})
            res = next((json.loads(e["output"]) for e in events if e["step"] == "resolve" and e["output"]), {})
            c2.markdown(f"**Category:** {inc['category']}  \n**Application:** {inc['cmdb_ci']}  \n**Impact / urgency:** {inc['impact']} / {inc['urgency']}  \n"
                        f"**Priority:** {inc['priority']} ({', '.join(prio.get('rules', []))})  \n**Resolver group:** {inc['assignment_group']}  \n"
                        f"**Confidence:** {cls.get('confidence')}  \n**Cited SOPs:** {', '.join(res.get('sop_ids', [])) or '–'}")
            c2.markdown("**Evidence**: " + "; ".join(f"“{q}”" for q in cls.get("evidence", [])))
            c2.error("**Why a human is needed:**\n" + "\n".join(f"- {r}" for r in (inc.get("gate_reasons") or "").split(";") if r))
            thread = (inc.get("work_notes") or "").split("thread:")[-1].strip()
            new_group = c2.selectbox("Reassign to", catalogue.groups, index=catalogue.groups.index(inc["assignment_group"]) if inc["assignment_group"] in catalogue.groups else 0, key=f"g{inc['number']}")
            b1, b2, b3, b4 = st.columns(4)
            decision = None
            if b1.button("Approve", key=f"a{inc['number']}"):
                decision = {"action": "approve", "reviewer": "reviewer"}
            if b2.button("Approve edited", key=f"e{inc['number']}"):
                decision = {"action": "edit", "response": proposed, "reviewer": "reviewer"}
            if b3.button("Reject → assign", key=f"x{inc['number']}"):
                decision = {"action": "reject", "comment": "needs a resolver", "reviewer": "reviewer"}
            if b4.button("Reassign", key=f"g2{inc['number']}"):
                decision = {"action": "reassign", "group": new_group, "reviewer": "reviewer"}
            if decision:
                if thread.startswith("T-"):
                    wf.resume(thread, decision)
                else:  # ticket created in batch mode: apply directly
                    wf.apply_review({"number": inc["number"], "resolution": {"response": proposed}}, decision)
                st.success(f"Decision recorded: {decision['action']}")
                st.rerun()

else:
    st.header("All tickets")
    rows = store.list_incidents()
    st.dataframe([{k: r[k] for k in ("number", "state", "priority", "category", "cmdb_ci", "assignment_group", "short_description")} for r in rows],
                 use_container_width=True)
    num = st.text_input("Show audit trail for ticket number")
    if num:
        st.dataframe(store.audit_events(num), use_container_width=True)
