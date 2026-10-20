"""Write summary.md: the values for the result tables of thesis chapter 4."""
from __future__ import annotations

import math


def _f(v, pct=False):
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "–"
    if isinstance(v, dict) and "mean" in v:
        m, sd = v["mean"], v["sd"]
        if m is None or (isinstance(m, float) and math.isnan(m)):
            return "–"
        return (f"{m*100:.1f} % (±{sd*100:.1f})" if pct else f"{m:.3f} (±{sd:.3f})")
    if isinstance(v, (int,)) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return f"{v*100:.1f} %" if pct else f"{v:.3f}"
    return str(v)


def write_markdown(s: dict, path) -> None:
    L = [f"# Experiment results – provider {s['provider']} ({s['model']}), {s['runs']} run(s)", "",
         f"Started {s['started']}; duration {s.get('duration_min')} min. Values: mean (± standard deviation over runs).", ""]
    if "E1" in s:
        e = s["E1"]
        L += ["## E1 – public ticket dataset D1 (thesis Table e1)", "", f"Test tickets: {e['n_test']}; training pool: {e['n_train']}", "",
              "| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |", "|---|---|---|---|"]
        for k, label in (("queue_accuracy", "Queue accuracy"), ("queue_macro_f1", "Queue macro-F1"), ("priority_accuracy", "Priority exact accuracy (P1–P3)"),
                         ("priority_macro_f1", "Priority macro-F1"), ("high_priority_under_prioritisation", "High-priority under-prioritisation rate")):
            pct = "f1" not in k
            L.append(f"| {label} | {_f(e['keyword'][k], pct)} | {_f(e['supervised'][k], pct)} | {_f(e['prototype'][k], pct)} |")
        L += ["", f"McNemar (run 1) prototype vs supervised: queue p = {e['mcnemar_run1']['queue']['p']:.4f}; priority p = {e['mcnemar_run1']['priority']['p']:.4f}",
              f"Leakage check – supervised baseline on a naive random split: queue {e['supervised_naive_split']['queue_accuracy']*100:.1f} %, priority {e['supervised_naive_split']['priority_accuracy']*100:.1f} %", ""]
    L += ["## E2 – controlled benchmark D2 test set (thesis Table e2)", "", "| Field | Keyword baseline | Prototype (LLM) |", "|---|---|---|"]
    for k, label in (("category_accuracy", "Category accuracy"), ("category_macro_f1", "Category macro-F1"), ("application_accuracy", "Application accuracy"),
                     ("application_macro_f1", "Application macro-F1"), ("impact_accuracy", "Impact accuracy"), ("urgency_accuracy", "Urgency accuracy"),
                     ("priority_accuracy", "Priority exact accuracy"), ("group_accuracy", "Resolver-group accuracy"),
                     ("whole_ticket_exact_match", "Whole-ticket exact match"), ("high_priority_under_prioritisation", "High-priority under-prioritisation rate")):
        pct = "f1" not in k
        L.append(f"| {label} | {_f(s['E2_keyword'][k], pct)} | {_f(s['E2_prototype'][k], pct)} |")
    L += ["", f"McNemar exact match prototype vs keyword (run 1): p = {s['E2_mcnemar_exact_match_vs_keyword']['p']:.4f}",
          f"Failure counts (run 1): {s['E2_failures_run1']}", "",
          "## E3/E4 – retrieval and resolution (thesis Table e34)", "", "| Metric | Without retrieval | With retrieval (RAG) |", "|---|---|---|",
          f"| Recall@3 (answerable cases) | – | {_f(s['E3']['recall_at_3'], True)} |", f"| Mean reciprocal rank | – | {_f(s['E3']['mrr'])} |"]
    e4 = s["E4"]
    L += [f"| Groundedness share 2 / 1 / 0 (LLM judge) | {e4['norag']['groundedness_share_2_1_0']} | {e4['rag']['groundedness_share_2_1_0']} |",
          f"| Mean key-step coverage | {_f(e4['norag']['mean_key_step_coverage'], True)} | {_f(e4['rag']['mean_key_step_coverage'], True)} |",
          f"| Abstention accuracy (unanswerable) | {_f(e4['norag']['abstention_accuracy_unanswerable'], True)} | {_f(e4['rag']['abstention_accuracy_unanswerable'], True)} |",
          "", "Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run `python -m src.experiments.agreement`.", "",
          "## E5 – selective automation (thesis Table e5, Figure riskcov)", "", f"Chosen on development set: {s['E5_chosen']}", ""]
    if s.get("E5_chosen_original") and s["E5_chosen_original"] != s["E5_chosen"]:
        L += [f"Originally chosen (before the tie-break correction): {s['E5_chosen_original']}", ""]
    L += [
          "| Metric | Result |", "|---|---|", f"| Thresholds τ₁ / τ₂ | {s['E5_chosen']['tau1']} / {s['E5_chosen']['tau2']} |"]
    t = s["E5_test"]
    L += [f"| Coverage (auto-eligible share) | {_f(t['coverage'], True)} |", f"| Accepted-case accuracy | {_f(t['accepted_accuracy'], True)} |",
          f"| Auto-eligible answers with groundedness 2 (run 1) | {_f(t.get('auto_groundedness_2_share_run1'), True)} |",
          f"| Unanswerable tickets handled automatically (count) | {_f(t['unanswerable_auto'])} |", f"| True P1 tickets handled automatically (count) | {_f(t['true_p1_auto'])} |",
          f"| Tickets expected to be automatable (gold) | {_f(t['expected_auto'])} |", "",
          "## E6 – challenge set (thesis Table e6)", "", "| Challenge type (n) | Correctly escalated | Injection detected | Auto-handled although escalation expected (count) | Blocked tool calls | Rejected by the LLM service |",
          "|---|---|---|---|---|---|"]
    for typ, d in s["E6"].items():
        L.append(f"| {typ} ({d['n']}) | {_f(d['escalated'], True)} | {_f(d['injection_detected'], True)} | {_f(d.get('auto_despite_escalation_expected', d.get('unauthorised_action')))} "
                 f"| {_f(d.get('blocked_tool_calls'))} | {_f(d.get('rejected_by_service'))} |")
    e7 = s["E7"]
    L += ["", "## E7 – efficiency and reliability (thesis Table e7)", "", "| Metric | Result |", "|---|---|",
          f"| Median / 95th-percentile end-to-end latency (s) | {e7['latency_median_s']} / {e7['latency_p95_s']} |",
          f"| Mean LLM calls per ticket | {e7['llm_calls_mean']} |", f"| Mean tokens per ticket | {e7['tokens_mean']} |",
          f"| Estimated cost per ticket (EUR) | {e7['cost_per_ticket_eur']} |", f"| Tickets with errors (share) | {_f(e7['tickets_with_errors_share'], True)} |",
          f"| LLM retries / schema repairs (total) | {e7['llm_retries_total']} / {e7['schema_repairs_total']} |",
          f"| Decisions with a complete audit record | {_f(e7['audit_complete_share'], True)} |", ""]
    if e7.get("errors_by_type"):
        L += [f"Errors on the challenge set by type (all runs): {e7['errors_by_type']}", ""]
    path.write_text("\n".join(L), encoding="utf-8")
