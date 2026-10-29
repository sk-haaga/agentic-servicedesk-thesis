"""Write summary.md: the values for the result tables of thesis chapter 4 (design iteration 2).

Data sets: D1 = public ticket dataset; D3 = controlled benchmark (calibration, test, challenge and attack
sets). Values are means over the repeated runs (± standard deviation) unless stated otherwise.
"""
from __future__ import annotations

import math


def _nan(v) -> bool:
    return v is None or (isinstance(v, float) and math.isnan(v))


def _f(v, pct=False, dec=3):
    if _nan(v):
        return "–"
    if isinstance(v, dict) and "mean" in v:
        m, sd = v["mean"], v.get("sd")
        if _nan(m):
            return "–"
        sd = 0.0 if _nan(sd) else sd
        return f"{m*100:.1f} % (±{sd*100:.1f})" if pct else f"{m:.{dec}f} (±{sd:.{dec}f})"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return f"{v*100:.1f} %" if pct else f"{v:.{dec}f}"
    return str(v)


def _ci(ci, pct=True):
    if not ci or any(_nan(x) for x in ci):
        return "–"
    return f"[{ci[0]*100:.1f}–{ci[1]*100:.1f}]" if pct else f"[{ci[0]:.3f}–{ci[1]:.3f}]"


def _p(p):
    return "–" if _nan(p) else ("< 0.0001" if p < 0.0001 else f"{p:.4f}")


def write_markdown(s: dict, path) -> None:
    L = [f"# Experiment results – provider {s.get('provider')} ({s.get('model')}), {s.get('runs')} run(s)", "",
         f"Results folder: {s.get('results_folder', '–')}. Started {s.get('started')}; duration {s.get('duration_min')} min.",
         "Values: mean over runs (± standard deviation over runs); [..] = 95 % confidence interval.", ""]
    if s.get("reanalysed"):
        L += [f"**Re-analysed {s['reanalysed']}.** {s.get('reanalysis_note', '')}", ""]

    # ------------------------------------------------------------------ E1
    if "E1" in s:
        e = s["E1"]
        ci = e.get("ci", e.get("ci_run1", {}))
        L += ["## E1 – public ticket dataset D1", "", f"Test tickets: {e['n_test']}; training pool: {e['n_train']}", "",
              "| Metric | Keyword baseline | Supervised baseline | Prototype (LLM) |", "|---|---|---|---|"]
        for k, label in (("queue_accuracy", "Queue accuracy"), ("queue_macro_f1", "Queue macro-F1"), ("priority_accuracy", "Priority exact accuracy (P1–P3)"),
                         ("priority_macro_f1", "Priority macro-F1"), ("high_priority_under_prioritisation", "High-priority under-prioritisation rate")):
            pct = "f1" not in k
            extra = {"queue_accuracy": ("keyword_queue", "supervised_queue", "prototype_queue"),
                     "priority_accuracy": ("keyword_priority", "supervised_priority", "prototype_priority")}.get(k)
            cells = [_f(e.get("keyword", {}).get(k), pct), _f(e.get("supervised", {}).get(k), pct), _f(e["prototype"][k], pct)]
            if extra:
                cells = [c + (" " + _ci(ci.get(x)) if ci.get(x) else "") for c, x in zip(cells, extra)]
            L.append(f"| {label} | " + " | ".join(cells) + " |")
        L.append("")
        if e.get("service_failures"):
            sf, ex = e["service_failures"], e.get("prototype_excluding_service_failures", {})
            L += [f"Service failures (classification call failed after all retries; counted as wrong above): {sf['total']} of "
                  f"{e['n_test'] * len(sf['per_run'])} ticket runs ({sf['share']*100:.1f} %). Without them: queue accuracy "
                  f"{_f(ex.get('queue_accuracy'), True)}, priority accuracy {_f(ex.get('priority_accuracy'), True)}, "
                  f"high-priority under-prioritisation {_f(ex.get('high_priority_under_prioritisation'), True)}.", ""]
        if e.get("mcnemar_summary"):
            L += ["Exact McNemar test in every run (b = prototype right / baseline wrong, c = the reverse):", "",
                  "| Comparison | mean b | mean c | largest p | runs with p < 0.05 |", "|---|---|---|---|---|"]
            for k, v in e["mcnemar_summary"].items():
                L.append(f"| {k.replace('_', ' ')} | {v['prototype_better_b_mean']} | {v['baseline_better_c_mean']} | {_p(v['p_max'])} | {v['runs_p_below_0.05']}/{v['runs']} |")
            L.append("")
        elif e.get("mcnemar_run1"):
            L += [f"McNemar (run 1) prototype vs supervised: queue p = {_p(e['mcnemar_run1']['queue']['p'])}; priority p = {_p(e['mcnemar_run1']['priority']['p'])}", ""]
        if e.get("supervised_naive_split"):
            n = e["supervised_naive_split"]
            L += [f"Leakage check – supervised baseline on a naive random split: queue {n['queue_accuracy']*100:.1f} %, priority {n['priority_accuracy']*100:.1f} %", ""]
        if e.get("E8_consistency"):
            L += _consistency_table("E8 – consistency of the D1 predictions across runs", e["E8_consistency"])

    # ------------------------------------------------------------------ E2
    if "E2_prototype" in s:
        cb = s.get("E2_card_bootstrap", {})
        L += ["## E2 – controlled benchmark D3, test set", "",
              f"Test emails: {s.get('n', {}).get('test', '–')} from {s.get('n_cards', {}).get('test', '–')} scenario cards; intervals resample whole cards.", "",
              "| Field | Keyword baseline | Prototype (LLM) | Prototype 95 % CI (cards) |", "|---|---|---|---|"]
        names = {"category": "Category", "application": "Application", "impact": "Impact", "urgency": "Urgency", "priority": "Priority", "group": "Resolver group"}
        for key, label in names.items():
            L.append(f"| {label} accuracy | {_f(s['E2_keyword'].get(f'{key}_accuracy'), True)} | {_f(s['E2_prototype'].get(f'{key}_accuracy'), True)} | "
                     f"{_ci(cb.get(f'prototype_{key}', {}).get('ci'))} |")
        for key, label in (("category_macro_f1", "Category macro-F1"), ("application_macro_f1", "Application macro-F1")):
            L.append(f"| {label} | {_f(s['E2_keyword'].get(key))} | {_f(s['E2_prototype'].get(key))} | |")
        L.append(f"| Whole-ticket exact match | {_f(s['E2_keyword'].get('whole_ticket_exact_match'), True)} {_ci(cb.get('keyword_exact', {}).get('ci'))} | "
                 f"{_f(s['E2_prototype'].get('whole_ticket_exact_match'), True)} | {_ci(cb.get('prototype_exact', {}).get('ci'))} |")
        L.append(f"| High-priority under-prioritisation | {_f(s['E2_keyword'].get('high_priority_under_prioritisation'), True)} | "
                 f"{_f(s['E2_prototype'].get('high_priority_under_prioritisation'), True)} | |")
        L.append("")
        if cb.get("difference"):
            d = cb["difference"]
            L += [f"Exact-match difference prototype − keyword: {d['mean']*100:.1f} points {_ci(d['ci'])} ({cb.get('clusters')} cards).", ""]
        if s.get("E2_card_sign_test_all_runs"):
            t = s["E2_card_sign_test_all_runs"]
            L += [f"Card-level sign test (all runs pooled): prototype better on {t['prototype_better']} cards, keyword better on {t['keyword_better']}; p = {_p(t['p'])}."]
        if s.get("E2_tests_summary"):
            t = s["E2_tests_summary"]
            L += [f"Per run: largest McNemar p (emails) = {_p(t['mcnemar_p_max'])}; largest card-level sign-test p = {_p(t['card_sign_test_p_max'])} ({t['runs']} runs)."]
        L += ["", f"Failure counts (run 1): {s.get('E2_failures_run1')}", f"Failure counts (all runs): {s.get('E2_failures_all_runs', '–')}", ""]
        if s.get("E2_service_failures"):
            sf, ex = s["E2_service_failures"], s.get("E2_prototype_excluding_service_failures", {})
            L += [f"Service failures (no classification; counted as wrong above): {sf['total']} ticket runs {sf['per_run']} "
                  f"({', '.join(sf['tickets'])}). Without them: whole-ticket exact match {_f(ex.get('whole_ticket_exact_match'), True)}, "
                  f"priority accuracy {_f(ex.get('priority_accuracy'), True)}, application accuracy {_f(ex.get('application_accuracy'), True)}, "
                  f"high-priority under-prioritisation {_f(ex.get('high_priority_under_prioritisation'), True)}.", ""]
        if s.get("E8_consistency_test"):
            L += _consistency_table("E8 – consistency of the D3 test predictions across runs", s["E8_consistency_test"])

    # ------------------------------------------------------------------ E3/E4
    if "E3" in s:
        L += ["## E3/E4 – retrieval and resolution (D3 test set)", "", "| Metric | Without retrieval | With retrieval (RAG) |", "|---|---|---|",
              f"| Recall@3 ({s['E3'].get('n_answerable')} answerable cases) | – | {_f(s['E3']['recall_at_3'], True)} |",
              f"| Mean reciprocal rank | – | {_f(s['E3']['mrr'])} |"]
        e4 = s.get("E4", {})
        if e4 and "share_2" in e4.get("rag", {}):
            for k, label in (("share_2", "Groundedness 2 – fully supported (LLM judge)"), ("share_1", "Groundedness 1"), ("share_0", "Groundedness 0 – significant unsupported step"),
                             ("key_step_coverage", "Key-step coverage (keyword match)"), ("abstention_accuracy_unanswerable", "Abstention on unanswerable tickets")):
                L.append(f"| {label} | {_f(e4.get('norag', {}).get(k), True)} | {_f(e4['rag'].get(k), True)} |")
        elif e4:
            L += [f"| Groundedness share 2 / 1 / 0 (LLM judge, run 1) | {e4['norag'].get('groundedness_share_2_1_0')} | {e4['rag'].get('groundedness_share_2_1_0')} |",
                  f"| Key-step coverage | {_f(e4['norag'].get('mean_key_step_coverage'), True)} | {_f(e4['rag'].get('mean_key_step_coverage'), True)} |",
                  f"| Abstention on unanswerable | {_f(e4['norag'].get('abstention_accuracy_unanswerable'), True)} | {_f(e4['rag'].get('abstention_accuracy_unanswerable'), True)} |"]
        L += ["", "Author agreement with the LLM judge: fill in e4_blind_scoring_sheet.csv and run "
              "`python -m src.experiments.agreement --folder <this folder>`.", ""]

    # ------------------------------------------------------------------ E5
    if "E5_chosen" in s:
        c = s["E5_chosen"]
        L += ["## E5 – selective automation", ""]
        if "rule" in c:
            L += [f"Thresholds chosen on the calibration set ({c.get('calibration_emails')} emails × {c.get('runs_pooled')} runs pooled; "
                  f"criterion '{c.get('criterion')}', target {c.get('target')}, at least {c.get('min_accepted')} accepted per run): "
                  f"**τ₁ = {c['tau1']}, τ₂ = {c['tau2']}** ({c['rule']}). Calibration coverage {c['dev_coverage']*100:.1f} %, "
                  f"accuracy {_f(c.get('dev_accepted_accuracy'), True)}, {c['dev_n_auto_mean']} accepted per run, lower bound {_f(c.get('dev_lower_bound'), True)}.", ""]
        else:
            L += [f"Chosen on development set: {c}", ""]
        if c.get("reference"):
            r = c["reference"]
            L += [f"Reference operating point (highest Clopper–Pearson lower bound with enough accepted tickets): τ₁ = {r['tau1']}, τ₂ = {r['tau2']}; "
                  f"calibration coverage {r['dev_coverage']*100:.1f} %, accuracy {r['dev_accepted_accuracy']*100:.1f} %, lower bound {_f(r.get('dev_lower_bound'), True)}.", ""]
        if s.get("analysis_point"):
            ap = s["analysis_point"]
            L += [f"Ablation (E5b) and security analysis (E6b) use τ₁ = {ap['tau1']}, τ₂ = {ap['tau2']}: {ap['what']}.", ""]
        if s.get("E5_chosen_original") and s["E5_chosen_original"] != c:
            L += [f"Originally chosen in this folder: {s['E5_chosen_original']}", ""]
        t = s["E5_test"]
        L += ["| Test set at the frozen thresholds | Result |", "|---|---|",
              f"| Coverage (share handled automatically) | {_f(t['coverage'], True)} {_ci(t.get('coverage_ci_exact'))} |",
              f"| Accepted-case accuracy | {_f(t['accepted_accuracy'], True)} {_ci(t.get('accepted_accuracy_ci_exact'))} |",
              f"| Tickets handled automatically per run | {_f(t.get('n_auto'), dec=1)} |",
              f"| Auto answers with groundedness 2 (LLM judge) | {_f(t.get('auto_groundedness_2_share', t.get('auto_groundedness_2_share_run1')), True)} |",
              f"| Unanswerable tickets handled automatically (count per run) | {_f(t['unanswerable_auto'], dec=1)} |",
              f"| True P1 tickets handled automatically (count per run) | {_f(t['true_p1_auto'], dec=1)} |",
              f"| Tickets expected to be automatable (gold) | {_f(t['expected_auto'], dec=0)} |", "",
              "Exact (Clopper–Pearson) intervals use the per-run average counts.", ""]
        if s.get("E5_test_reference"):
            t = s["E5_test_reference"]
            L += ["Test set at the reference operating point (for comparison; not the deployed setting):", "",
                  f"coverage {_f(t['coverage'], True)} {_ci(t.get('coverage_ci_exact'))}; accepted-case accuracy {_f(t['accepted_accuracy'], True)} "
                  f"{_ci(t.get('accepted_accuracy_ci_exact'))}; unanswerable auto {_f(t['unanswerable_auto'], dec=1)}; true P1 auto {_f(t['true_p1_auto'], dec=1)} per run.", ""]
            if t.get("accepted_accuracy_ignoring_category"):
                L += [f"Secondary, post hoc: accepted-case accuracy when the category label is not required (priority, application, "
                      f"resolver group and SOP still must be right): {_f(t['accepted_accuracy_ignoring_category'], True)}.", ""]
        if s.get("E5_test_curve_post_hoc"):
            L += ["Post hoc test-set curve at the analysis τ₁ (sensitivity only, not used for the choice):", "",
                  "| τ₂ | Coverage | Accepted-case accuracy | Unanswerable auto (per run) |", "|---|---|---|---|"]
            for r in s["E5_test_curve_post_hoc"]:
                L.append(f"| {r['tau2']} | {_f(r['coverage'], True)} | {_f(r['accepted_accuracy'], True)} | {_f(r['unanswerable_auto'], dec=1)} |")
            L.append("")
        if s.get("E8_gate_consistency_test"):
            g = s["E8_gate_consistency_test"]
            L += [f"Gate decision consistency on the test set (at the analysis point): same decision in all runs for {g['unanimous_share']*100:.1f} % of tickets; "
                  f"{g['items_changed_at_least_once']} tickets changed at least once; Fleiss κ = {_f(g.get('fleiss_kappa'))}.", ""]
    if s.get("E5b_guardrail_ablation"):
        L += ["## E5b – guardrail ablation (one gate condition switched off at a time; stored outputs, mean per run)", "",
              "| Gate | Test coverage | Test accepted accuracy | Unanswerable auto | True P1 auto | Challenge auto | Attack auto |", "|---|---|---|---|---|---|---|"]
        for k, row in s["E5b_guardrail_ablation"].items():
            te, ch, at = row.get("test", {}), row.get("challenge", {}), row.get("attack", {})
            L.append(f"| {k.replace('_', ' ')} | {_f(te.get('coverage'), True)} | {_f(te.get('accepted_accuracy'), True)} | {_f(te.get('unanswerable_auto'), dec=1)} | "
                     f"{_f(te.get('true_p1_auto'), dec=1)} | {_f(ch.get('n_auto'), dec=1)} | {_f(at.get('n_auto'), dec=1)} |")
        L.append("")

    # ------------------------------------------------------------------ E6
    if s.get("E6"):
        L += ["## E6 – challenge and attack sets (at the analysis point named under E5)", "",
              "| Type (n) | Correctly escalated | Injection detected | by pattern screen | by LLM flag | Auto although escalation expected | Blocked tool calls | Rejected by the LLM service |",
              "|---|---|---|---|---|---|---|---|"]
        for typ, d in s["E6"].items():
            L.append(f"| {typ} ({d['n']}) | {_f(d['escalated'], True)} | {_f(d['injection_detected'], True)} | {_f(d.get('detected_by_pattern_screen'), True)} | "
                     f"{_f(d.get('detected_by_llm_flag'), True)} | {_f(d.get('auto_despite_escalation_expected', d.get('unauthorised_action')), dec=1)} | "
                     f"{_f(d.get('blocked_tool_calls'), dec=1)} | {_f(d.get('rejected_by_service'), dec=1)} |")
        L.append("")
    if s.get("E6b_security"):
        L += ["## E6b – attack success with and without defences", "",
              "An attack succeeds if the ticket is handled automatically, its triage is changed from the gold labels, the reply follows the payload "
              "or leaks the prompt, or a tool outside the allow-list is requested. 'Undefended' = no pattern screen, no prompt-level defences, "
              "gate ignores injection flags (tool allow-list and the other gate conditions stay on).", "",
              "| Condition | Set (n) | Any success | Auto-handled | Triage changed | Payload in reply (draft) | Payload in an automatic reply | Unauthorised tool | Detected |",
              "|---|---|---|---|---|---|---|---|---|"]
        for cond, sets in s["E6b_security"].items():
            for name, d in sets.items():
                L.append(f"| {cond} | {name} ({d.get('n')}) | {_f(d['any_success'], True)} | {_f(d['auto_handled'], True)} | {_f(d['triage_manipulated'], True)} | "
                         f"{_f(d['payload_in_reply'], True)} | {_f(d.get('payload_in_automatic_reply'), True)} | {_f(d['unauthorised_tool_requested'], True)} | "
                         f"{_f(d['detected'], True)} |")
        L += ["", "'Triage changed' also counts ordinary classification errors; compare the two conditions rather than reading it alone.", ""]

    # ------------------------------------------------------------------ E7
    if s.get("E7"):
        e7 = s["E7"]
        L += ["## E7 – efficiency and reliability", "", "| Metric | Result |", "|---|---|",
              f"| Ticket runs (D3, with defences) | {e7.get('tickets')} |",
              f"| Median / 95th-percentile end-to-end latency (s) | {e7['latency_median_s']} / {e7['latency_p95_s']} (parallel workers: {e7.get('workers', '–')}) |",
              f"| Mean LLM calls per ticket | {e7['llm_calls_mean']} |", f"| Mean tokens per ticket | {e7['tokens_mean']} |",
              f"| Estimated cost per ticket (EUR) | {e7['cost_per_ticket_eur']} (price basis per million tokens: {e7.get('price_basis', '–')}) |",
              f"| Tickets with errors (share) | {_f(e7['tickets_with_errors_share'], True)} |",
              f"| LLM retries / schema repairs (total) | {e7['llm_retries_total']} / {e7['schema_repairs_total']} |",
              f"| Decisions with a complete audit record | {_f(e7['audit_complete_share'], True)} |", ""]
        if e7.get("errors_by_type"):
            L += [f"Errors by type: {e7['errors_by_type']}", ""]
    if s.get("usage", {}).get("models"):
        L += [f"Model versions reported by the API (calls): {s['usage']['models']}; embeddings: {s['usage'].get('embed_models')}", ""]
    path.write_text("\n".join(L), encoding="utf-8")


def _consistency_table(title: str, d: dict) -> list[str]:
    L = [f"### {title}", "", "| Field | Same in all runs | Items changed at least once | Mean agreement with majority | Fleiss κ | Majority-vote accuracy | Mean run accuracy |",
         "|---|---|---|---|---|---|---|"]
    for k, v in d.items():
        L.append(f"| {k.replace('pred_', '')} | {_f(v['unanimous_share'], True)} | {v['items_changed_at_least_once']} of {v['items']} | "
                 f"{_f(v['mean_agreement_with_majority'], True)} | {_f(v.get('fleiss_kappa'))} | {_f(v.get('majority_vote_accuracy'), True)} | "
                 f"{_f(v.get('mean_run_accuracy'), True)} |")
    return L + [""]
