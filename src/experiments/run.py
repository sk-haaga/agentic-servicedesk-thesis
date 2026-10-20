"""Experiment runner for E1-E7 (thesis chapter 3.4, results in chapter 4.3-4.6).

    python -m src.experiments.run --provider azure --runs 3          # full evaluation
    python -m src.experiments.run --provider fake --runs 1 --limit 20  # quick offline smoke test

Outputs to results/<provider>/: per-case CSV files, summary.json, summary.md (values for the thesis
tables) and figures/*.png. Thresholds are chosen on the D2 development set (E5) and then applied once
to the test and challenge sets; the gate is deterministic, so it is re-applied offline to the stored
features of each case.
"""
from __future__ import annotations

import argparse
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

from ..baselines.keyword import classify as kw_classify
from ..baselines.supervised import SupervisedBaseline
from ..servicedesk import gate as gate_mod
from ..servicedesk.config import ROOT, env, load_catalogue
from ..servicedesk.email_intake import from_fields
from ..servicedesk.itsm.store import Store
from ..servicedesk.knowledge import KnowledgeBase, load_sops
from ..servicedesk.llm import get_llm
from ..servicedesk.prompts import JUDGE_SYSTEM, JUDGE_USER
from ..servicedesk.rules import compute_priority, route
from ..servicedesk.schemas import Judgement, Resolution
from ..servicedesk.workflow import ServiceDeskWorkflow
from . import metrics as M

PRIOS = ["P1", "P2", "P3"]
STEPS = ["intake_guard", "create_ticket", "classify", "prioritise", "route", "retrieve", "resolve", "gate"]


# ----------------------------------------------------------------------------- data
def load_d1(split: str) -> pd.DataFrame:
    path = ROOT / "data" / "processed" / f"d1_{split}.csv"
    if not path.exists():
        raise SystemExit("D1 not prepared. Run: python -m src.data_prep.prepare_d1")
    return pd.read_csv(path)


def load_d2() -> pd.DataFrame:
    path = ROOT / "data" / "d2" / "benchmark.jsonl"
    if not path.exists():
        raise SystemExit("D2 not built. Run: python -m src.data_prep.build_d2")
    return pd.read_json(path, lines=True)


# ----------------------------------------------------------------------------- running cases
def run_cases(wf: ServiceDeskWorkflow, df: pd.DataFrame, workers: int) -> pd.DataFrame:
    def one(row):
        t0 = time.perf_counter()
        st = wf.process(from_fields(row.get("subject"), row.get("body")), case_id=str(row["id"]))
        c = st.get("classification") or {}
        res = st.get("resolution") or {}
        sops = st.get("sops") or []
        return {
            "id": row["id"], "pred_category": c.get("category"), "pred_application": c.get("application"),
            "pred_impact": c.get("impact"), "pred_urgency": c.get("urgency"), "pred_priority": st.get("priority"),
            "pred_group": st.get("group"), "confidence": c.get("confidence"), "llm_injection": c.get("injection_suspected"),
            "guard_hits": len(st.get("injection_hits") or []), "retrieved": [s["sop_id"] for s in sops[:3]],
            "top_similarity": max([s["similarity"] for s in sops] or [0.0]), "answerable": res.get("answerable"),
            "sop_ids": res.get("sop_ids") or [], "self_check": res.get("self_check"), "response": res.get("response", ""),
            "human_requested": bool(res.get("human_requested")), "blocked_tools": len(st.get("blocked_tools") or []),
            "errors": ";".join(st.get("errors") or []), "route_run": st.get("final_state"), "number": st.get("number"),
            "llm_calls": st.get("llm_calls", 0), "tokens_in": st.get("tokens_in", 0), "tokens_out": st.get("tokens_out", 0),
            "latency_s": round(time.perf_counter() - t0, 3)}
    rows = [r for _, r in df.iterrows()]
    if workers > 1:
        with ThreadPoolExecutor(workers) as ex:
            out = list(ex.map(one, rows))
    else:
        out = [one(r) for r in rows]
    return pd.DataFrame(out)


def regate(df: pd.DataFrame, catalogue, tau1: float, tau2: float) -> pd.Series:
    """Re-apply the deterministic gate to stored features with given thresholds."""
    routes = []
    for _, r in df.iterrows():
        if not r.get("pred_priority"):
            routes.append("human"); continue
        res = Resolution(answerable=bool(r["answerable"]), sop_ids=list(r["sop_ids"]), response=r["response"] or "",
                         self_check=r["self_check"] or "not_covered") if r["answerable"] is not None and not _isnan(r["answerable"]) else None
        errors = [e for e in str(r["errors"] or "").split(";") if e and e != "nan"]
        if r.get("human_requested"):
            errors.append("agent_requested_human")
        if r.get("blocked_tools", 0):
            errors.append("blocked_tool_call")
        d = gate_mod.decide(priority=r["pred_priority"], category=r["pred_category"], confidence=float(r["confidence"] or 0),
                            top_similarity=float(r["top_similarity"] or 0), resolution=res,
                            injection=bool(r["guard_hits"]) or bool(r["llm_injection"]), errors=errors, catalogue=catalogue,
                            tau1=tau1, tau2=tau2)
        routes.append(d.route)
    return pd.Series(routes, index=df.index)


def _isnan(x) -> bool:
    return isinstance(x, float) and math.isnan(x)


# ----------------------------------------------------------------------------- experiments
def e1_public(llm, runs: int, workers: int, limit: int | None, out: Path) -> dict:
    test, train = load_d1("test"), load_d1("train")
    if limit:
        test = test.head(limit)
    test = test.assign(id=test["row_id"])
    cat = load_catalogue("d1")
    res = {"n_test": len(test), "n_train": len(train)}
    # keyword baseline
    kw = [kw_classify(f"{s}\n{b}", cat) for s, b in zip(test["subject"].fillna(""), test["body"])]
    kw_q = [k["application"] for k in kw]
    kw_p = [compute_priority(k["impact"], k["urgency"], k["category"], cat)[0] for k in kw]
    # supervised baseline (trained on the leakage-free training pool)
    sup = SupervisedBaseline().fit(train).predict(test)
    res["keyword"] = _triage_scores(test["queue"], kw_q, test["priority_p"], kw_p)
    res["supervised"] = _triage_scores(test["queue"], sup["queue"], test["priority_p"], sup["priority_p"])
    # leakage illustration: the same classifier evaluated on a naive random split of the same pool
    res["supervised_naive_split"] = _naive_split_scores()
    # prototype
    per_run, frames = [], []
    for r in range(runs):
        wf = ServiceDeskWorkflow(llm, catalogue=cat, store=Store(out / "runs" / f"e1_r{r}.db"), triage_only=True, run_id=f"e1r{r}")
        df = run_cases(wf, test, workers)
        df["run"] = r
        frames.append(df)
        per_run.append(_triage_scores(test["queue"].tolist(), df["pred_application"].tolist(), test["priority_p"].tolist(), df["pred_priority"].tolist()))
    allp = pd.concat(frames)
    allp.merge(test[["id", "queue", "priority_p"]], on="id").to_csv(out / "e1_cases.csv", index=False)
    res["prototype"] = {k: M.summarise_runs([p[k] for p in per_run]) for k in per_run[0]}
    first = frames[0]
    yq, yp = test["queue"].tolist(), test["priority_p"].tolist()
    proto_q = [a == b for a, b in zip(yq, first["pred_application"])]
    proto_p = [a == b for a, b in zip(yp, first["pred_priority"])]
    sup_q = [a == b for a, b in zip(yq, sup["queue"])]
    sup_p = [a == b for a, b in zip(yp, sup["priority_p"])]
    res["ci_run1"] = {"prototype_queue": M.bootstrap_ci(proto_q), "prototype_priority": M.bootstrap_ci(proto_p),
                      "supervised_queue": M.bootstrap_ci(sup_q), "supervised_priority": M.bootstrap_ci(sup_p)}
    res["mcnemar_run1"] = {"queue": M.mcnemar(proto_q, sup_q), "priority": M.mcnemar(proto_p, sup_p)}
    res["confusion_priority_run1"] = {"labels": PRIOS, "prototype": M.conf_matrix(yp, first["pred_priority"], PRIOS),
                                      "supervised": M.conf_matrix(yp, sup["priority_p"], PRIOS)}
    return res


def _naive_split_scores() -> dict:
    from sklearn.model_selection import train_test_split
    pool = pd.concat([load_d1("train"), load_d1("dev"), load_d1("test")])
    tr, te = train_test_split(pool, test_size=400, random_state=42, stratify=pool["queue"] + "|" + pool["priority_p"])
    p = SupervisedBaseline().fit(tr).predict(te)
    return {"queue_accuracy": round(M.acc(te["queue"], p["queue"]), 4), "priority_accuracy": round(M.acc(te["priority_p"], p["priority_p"]), 4)}


def _triage_scores(yq, pq, yp, pp) -> dict:
    yq, pq, yp, pp = list(yq), list(pq), list(yp), [x if isinstance(x, str) else "none" for x in pp]
    pq = [x if isinstance(x, str) else "none" for x in pq]
    return {"queue_accuracy": round(M.acc(yq, pq), 4), "queue_macro_f1": round(M.macro_f1(yq, pq), 4),
            "priority_accuracy": round(M.acc(yp, pp), 4), "priority_macro_f1": round(M.macro_f1(yp, pp), 4),
            "high_priority_under_prioritisation": round(M.under_prioritisation(yp, pp), 4)}


def d2_fields(gold: pd.DataFrame, pred: pd.DataFrame) -> dict:
    g = gold.set_index("id").loc[pred["id"]]
    s = lambda col: [x if isinstance(x, str) else "none" for x in pred[col]]
    out = {
        "category_accuracy": M.acc(g["category"], s("pred_category")), "category_macro_f1": M.macro_f1(g["category"], s("pred_category")),
        "application_accuracy": M.acc(g["application"], s("pred_application")), "application_macro_f1": M.macro_f1(g["application"], s("pred_application")),
        "impact_accuracy": M.acc(g["impact"], s("pred_impact")), "urgency_accuracy": M.acc(g["urgency"], s("pred_urgency")),
        "priority_accuracy": M.acc(g["priority"], s("pred_priority")), "group_accuracy": M.acc(g["group"], s("pred_group")),
        "high_priority_under_prioritisation": M.under_prioritisation(g["priority"].tolist(), s("pred_priority")),
    }
    exact = [(a == b and c == d and e == f and h == i) for a, b, c, d, e, f, h, i in
             zip(g["category"], s("pred_category"), g["application"], s("pred_application"), g["priority"], s("pred_priority"), g["group"], s("pred_group"))]
    out["whole_ticket_exact_match"] = float(np.mean(exact))
    return {k: round(float(v), 4) for k, v in out.items()}


def keyword_d2(gold: pd.DataFrame) -> pd.DataFrame:
    cat = load_catalogue("d2")
    rows = []
    for _, r in gold.iterrows():
        k = kw_classify(f"{r['subject']}\n{r['body']}", cat)
        p, _ = compute_priority(k["impact"], k["urgency"], k["category"], cat)
        g, _ = route(k["application"], k["category"], cat)
        rows.append({"id": r["id"], "pred_category": k["category"], "pred_application": k["application"], "pred_impact": k["impact"],
                     "pred_urgency": k["urgency"], "pred_priority": p, "pred_group": g})
    return pd.DataFrame(rows)


def is_correct(gold_row, r) -> bool:
    """A ticket handled automatically is correct if triage is right and the cited SOP is the expected one."""
    triage = (r["pred_category"] == gold_row["category"] and r["pred_application"] == gold_row["application"]
              and r["pred_priority"] == gold_row["priority"] and r["pred_group"] == gold_row["group"])
    grounded = bool(gold_row["answerable"]) and gold_row["sop"] in list(r["sop_ids"] or [])
    return bool(triage and grounded)


def judge(llm, sop_text: str, response: str) -> int | None:
    if not response:
        return None
    overlap = len(set(response.lower().split()) & set(sop_text.lower().split())) / max(1, len(set(response.lower().split())))
    try:
        r = llm.parse(JUDGE_SYSTEM, JUDGE_USER.format(sop=sop_text, response=response), Judgement, context={"overlap": overlap})
        return int(r.parsed.score)
    except Exception:
        return None


def risk_coverage(dev: pd.DataFrame, gold: pd.DataFrame, cat) -> tuple[pd.DataFrame, dict]:
    g = gold.set_index("id")
    sims = dev["top_similarity"].astype(float)
    tau2_grid = sorted(set(np.round(np.quantile(sims, np.linspace(0, 0.9, 10)), 3)))
    tau1_grid = [round(x, 2) for x in np.arange(0.5, 0.96, 0.05)]
    rows = []
    for t1 in tau1_grid:
        for t2 in tau2_grid:
            routes = regate(dev, cat, t1, t2)
            acc_mask = routes == "auto"
            n_auto = int(acc_mask.sum())
            correct = sum(is_correct(g.loc[i], r) for i, r in dev[acc_mask].set_index("id").iterrows()) if n_auto else 0
            rows.append({"tau1": t1, "tau2": float(t2), "coverage": n_auto / len(dev), "accepted_accuracy": (correct / n_auto) if n_auto else float("nan"), "n_auto": n_auto})
    grid = pd.DataFrame(rows)
    ok = grid[(grid["accepted_accuracy"] >= 0.95) & (grid["n_auto"] > 0)]
    # Ties are broken towards the STRICTER thresholds (higher tau1, then higher tau2): when the development set
    # cannot tell two settings apart, the safer one is kept. (Before 2026-10-15 the fallback branch lacked this
    # tie-break and picked the loosest tau1 among equals; see thesis section 4.3.4.)
    best = (ok.sort_values(["coverage", "tau1", "tau2"], ascending=False).iloc[0] if len(ok)
            else grid.dropna().sort_values(["accepted_accuracy", "coverage", "tau1", "tau2"], ascending=False).iloc[0])
    return grid, {"tau1": float(best["tau1"]), "tau2": float(best["tau2"]), "dev_coverage": round(float(best["coverage"]), 4),
                  "dev_accepted_accuracy": round(float(best["accepted_accuracy"]), 4), "target_met": bool(len(ok))}


def selective_automation(frames: dict, gold: pd.DataFrame, cat, blind: list[dict], out: Path) -> dict:
    """E5 (thresholds chosen on dev run 1, frozen, applied to test) and E6 (challenge set at the frozen thresholds).
    Uses only stored per-case features, so it can be recomputed without new LLM calls (--reanalyse)."""
    res: dict = {}
    grid, chosen = risk_coverage(frames["dev"][0], gold, cat)
    grid.to_csv(out / "e5_threshold_grid.csv", index=False)
    res["E5_chosen"] = chosen
    e5 = []
    judged = {b["id"]: b["llm_score"] for b in blind if b["condition"] == "rag"}
    g = gold.set_index("id")
    for f in frames["test"]:
        f = f.reset_index(drop=True)
        routes = regate(f, cat, chosen["tau1"], chosen["tau2"])
        auto = f[routes == "auto"].set_index("id")
        n_auto = len(auto)
        correct = sum(is_correct(g.loc[i], r) for i, r in auto.iterrows())
        e5.append({"coverage": n_auto / len(f), "accepted_accuracy": correct / n_auto if n_auto else float("nan"),
                   "unanswerable_auto": int(sum(not g.loc[i, "answerable"] for i in auto.index)),
                   "true_p1_auto": int(sum(g.loc[i, "priority"] == "P1" for i in auto.index)),
                   "expected_auto": int((g.loc[f["id"], "expected_route"] == "auto").sum())})
    res["E5_test"] = {k: M.summarise_runs([e[k] for e in e5]) for k in e5[0]}
    f0 = frames["test"][0].reset_index(drop=True)
    auto1 = f0[regate(f0, cat, chosen["tau1"], chosen["tau2"]) == "auto"]["id"]
    sc = [judged.get(i) for i in auto1 if judged.get(i) is not None and not _isnan(judged.get(i))]
    res["E5_test"]["auto_groundedness_2_share_run1"] = round(sc.count(2) / len(sc), 4) if sc else None
    _plot_risk_coverage(grid, chosen, out)

    e6 = {}
    for f in frames["challenge"]:
        f = f.reset_index(drop=True)
        routes = regate(f, cat, chosen["tau1"], chosen["tau2"])
        f = f.assign(route=routes.values, type=g.loc[f["id"], "type"].values)
        for t, grp in f.groupby("type"):
            d = e6.setdefault(t, {"n": len(grp), "escalated": [], "injection_detected": [], "auto_despite_escalation_expected": [],
                                  "blocked_tool_calls": [], "rejected_by_service": []})
            d["escalated"].append(float((grp["route"] == "human").mean()))
            d["injection_detected"].append(float(((grp["guard_hits"] > 0) | (grp["llm_injection"] == True)).mean()))  # noqa: E712
            d["auto_despite_escalation_expected"].append(int((grp["route"] == "auto").sum()))
            d["blocked_tool_calls"].append(int(grp["blocked_tools"].sum()))
            d["rejected_by_service"].append(int(grp["errors"].fillna("").str.contains("BadRequest").sum()))
    keys = ("escalated", "injection_detected", "auto_despite_escalation_expected", "blocked_tool_calls", "rejected_by_service")
    res["E6"] = {t: {"n": d["n"], **{k: M.summarise_runs(d[k]) for k in keys}} for t, d in e6.items()}
    return res


def e2_to_e7(llm, runs: int, workers: int, limit: int | None, out: Path) -> dict:
    gold = load_d2()
    cat = load_catalogue("d2")
    kb = KnowledgeBase(llm)
    sop_text = {s.sop_id: s.text for s in load_sops()}
    dev, test, chal = (gold[gold["split"] == s] for s in ("dev", "test", "challenge"))
    if limit:
        dev, test, chal = dev.head(limit), test.head(limit), chal.head(limit)
    res: dict = {"n": {"dev": len(dev), "test": len(test), "challenge": len(chal)}}

    # ---- E2 keyword baseline (deterministic)
    kwp = keyword_d2(test)
    res["E2_keyword"] = d2_fields(gold, kwp)

    # ---- full pipeline runs (RAG) on dev, test, challenge; no-RAG ablation on test
    frames = {"dev": [], "test": [], "challenge": [], "test_norag": []}
    for r in range(runs):
        store = Store(out / "runs" / f"d2_r{r}.db")
        wf = ServiceDeskWorkflow(llm, catalogue=cat, store=store, kb=kb, run_id=f"d2r{r}")
        wf_norag = ServiceDeskWorkflow(llm, catalogue=cat, store=store, kb=kb, use_rag=False, run_id=f"d2r{r}n")
        for name, df, w in (("dev", dev, wf), ("test", test, wf), ("challenge", chal, wf), ("test_norag", test, wf_norag)):
            pdf = run_cases(w, df, workers)
            pdf["run"] = r
            frames[name].append(pdf)
    for name, fs in frames.items():
        pd.concat(fs).to_json(out / f"d2_{name}_cases.jsonl", orient="records", lines=True)

    # ---- E2 prototype triage
    res["E2_prototype"] = {k: M.summarise_runs([d2_fields(gold, f)[k] for f in frames["test"]]) for k in d2_fields(gold, frames["test"][0])}
    first = frames["test"][0]
    gt = gold.set_index("id").loc[first["id"]]
    res["E2_confusion_priority_run1"] = {"labels": PRIOS, "matrix": M.conf_matrix(gt["priority"], first["pred_priority"].fillna("none"), PRIOS)}
    res["E2_mcnemar_exact_match_vs_keyword"] = M.mcnemar(
        [bool(a) for a in _exact(gold, first)], [bool(a) for a in _exact(gold, kwp.set_index("id").loc[first["id"]].reset_index())])
    res["E2_failures_run1"] = _failure_types(gold, first)

    # ---- E3 retrieval (answerable test cases)
    ans = gt[gt["answerable"]]
    rec, mr = [], []
    for f in frames["test"]:
        ff = f.set_index("id").loc[ans.index]
        rec.append(M.recall_at_k(ans["sop"].tolist(), ff["retrieved"].tolist(), 3))
        mr.append(M.mrr(ans["sop"].tolist(), ff["retrieved"].tolist()))
    res["E3"] = {"recall_at_3": M.summarise_runs(rec), "mrr": M.summarise_runs(mr), "n_answerable": len(ans)}

    # ---- E4 RAG ablation (run 1; judged by LLM, blind CSV exported for the author)
    e4 = {}
    blind = []
    for cond, f in (("rag", frames["test"][0]), ("norag", frames["test_norag"][0])):
        f = f.set_index("id")
        g = gold.set_index("id").loc[f.index]
        scores, cov, abst = [], [], []
        for i, row in f.iterrows():
            gr = g.loc[i]
            if gr["answerable"]:
                if row["answerable"] and row["response"]:
                    s = judge(llm, sop_text[gr["sop"]], row["response"])
                    scores.append(s)
                    blind.append({"item": None, "id": i, "condition": cond, "sop_id": gr["sop"], "sop_text": sop_text[gr["sop"]], "response": row["response"], "llm_score": s})
                cov.append(M.key_step_coverage(row["response"] if row["answerable"] else "", gr["expected_steps"]))
            else:
                abst.append(not bool(row["answerable"]))
        sc = [s for s in scores if s is not None]
        e4[cond] = {"answered_answerable": len(sc), "groundedness_share_2_1_0": [round(sc.count(k) / len(sc), 4) if sc else None for k in (2, 1, 0)],
                    "mean_key_step_coverage": round(float(np.nanmean(cov)), 4) if cov else None,
                    "abstention_accuracy_unanswerable": round(float(np.mean(abst)), 4) if abst else None}
    res["E4"] = e4
    bdf = pd.DataFrame(blind).sample(frac=1, random_state=7).reset_index(drop=True)
    bdf["item"] = range(1, len(bdf) + 1)
    bdf.drop(columns=["condition", "llm_score"]).assign(author_score="").to_csv(out / "e4_blind_scoring_sheet.csv", index=False)
    bdf.to_csv(out / "e4_blind_key.csv", index=False)

    res.update(selective_automation(frames, gold, cat, blind, out))

    # ---- E7 efficiency and reliability (all full-pipeline runs)
    allf = pd.concat([pd.concat(frames[n]) for n in ("dev", "test", "challenge")])
    pin, pout, pemb = (float(env(k, "0") or 0) for k in ("PRICE_INPUT_PER_M", "PRICE_OUTPUT_PER_M", "PRICE_EMBED_PER_M"))
    res["E7"] = {"tickets": len(allf), "latency_median_s": round(float(allf["latency_s"].median()), 3),
                 "latency_p95_s": round(float(allf["latency_s"].quantile(0.95)), 3), "llm_calls_mean": round(float(allf["llm_calls"].mean()), 2),
                 "tokens_mean": round(float((allf["tokens_in"] + allf["tokens_out"]).mean()), 1),
                 "cost_per_ticket_eur": round(float((allf["tokens_in"].mean() * pin + allf["tokens_out"].mean() * pout) / 1e6), 6),
                 "tickets_with_errors_share": round(float((allf["errors"].fillna("") != "").mean()), 4),
                 "llm_retries_total": int(getattr(llm.usage, "retries", 0)), "schema_repairs_total": int(getattr(llm.usage, "repairs", 0)),
                 "audit_complete_share": _audit_completeness(out)}
    return res


def _exact(gold, pred):
    g = gold.set_index("id").loc[pred["id"]]
    return [(a == b and c == d and e == f and h == i) for a, b, c, d, e, f, h, i in
            zip(g["category"], pred["pred_category"], g["application"], pred["pred_application"], g["priority"], pred["pred_priority"], g["group"], pred["pred_group"])]


def _failure_types(gold, pred) -> dict:
    g = gold.set_index("id").loc[pred["id"]]
    counts = {"wrong_application": 0, "wrong_category": 0, "wrong_impact": 0, "wrong_urgency": 0, "wrong_priority": 0, "wrong_group": 0}
    for (_, gr), (_, pr) in zip(g.iterrows(), pred.iterrows()):
        for k, gk, pk in (("wrong_application", "application", "pred_application"), ("wrong_category", "category", "pred_category"),
                          ("wrong_impact", "impact", "pred_impact"), ("wrong_urgency", "urgency", "pred_urgency"),
                          ("wrong_priority", "priority", "pred_priority"), ("wrong_group", "group", "pred_group")):
            counts[k] += int(gr[gk] != pr[pk])
    return counts


def _audit_completeness(out: Path) -> float:
    import sqlite3
    ok = total = 0
    for db in (out / "runs").glob("d2_r*.db"):
        conn = sqlite3.connect(db)
        steps = pd.read_sql("SELECT ticket, step FROM audit_event", conn)
        for _, grp in steps.groupby("ticket"):
            total += 1
            s = set(grp["step"])
            ok += int(all(x in s for x in STEPS) and ({"auto_resolve", "human_review_requested"} & s != set()))
    return round(ok / total, 4) if total else float("nan")


# ----------------------------------------------------------------------------- figures
def _font():
    import logging
    import matplotlib
    logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
    matplotlib.rcParams["font.family"] = ["Arial", "Liberation Sans", "DejaVu Sans"]


def _plot_risk_coverage(grid: pd.DataFrame, chosen: dict, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _font()
    fig, ax = plt.subplots(figsize=(6.4, 4), dpi=200)
    g = grid[(grid["tau1"] == chosen["tau1"]) & (grid["n_auto"] > 0)].sort_values("coverage")
    ax.plot(g["coverage"] * 100, g["accepted_accuracy"] * 100, marker="o", color="#1f5c99", label=f"τ₁ = {chosen['tau1']}, varying τ₂")
    ax.scatter([chosen["dev_coverage"] * 100], [chosen["dev_accepted_accuracy"] * 100], s=90, color="#b04a3a", zorder=3,
               label=f"chosen: τ₂ = {chosen['tau2']}")
    ax.axhline(95, ls="--", color="#888", lw=0.8)
    ax.set_xlabel("Coverage: tickets handled automatically (%)")
    ax.set_ylabel("Accepted-case accuracy (%)")
    ax.legend(frameon=False, fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    (out / "figures").mkdir(exist_ok=True)
    fig.savefig(out / "figures" / "risk_coverage.png")


def plot_confusion(matrix, labels, path: Path, title: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _font()
    m = np.array(matrix)
    fig, ax = plt.subplots(figsize=(3.8, 3.4), dpi=200)
    ax.imshow(m, cmap="Blues")
    for i in range(len(labels)):
        for j in range(len(labels)):
            ax.text(j, i, str(m[i, j]), ha="center", va="center", color="white" if m[i, j] > m.max() / 2 else "#1b232b", fontsize=11)
    ax.set_xticks(range(len(labels)), labels)
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("Predicted priority")
    ax.set_ylabel("True priority")
    ax.set_title(title, fontsize=9)
    fig.tight_layout()
    fig.savefig(path)


# ----------------------------------------------------------------------------- re-analysis
def reanalyse(provider: str) -> None:
    out = ROOT / "results" / provider
    summary = json.loads((out / "summary.json").read_text())
    gold = load_d2()
    frames = {n: [g.reset_index(drop=True) for _, g in pd.read_json(out / f"d2_{n}_cases.jsonl", lines=True).groupby("run")]
              for n in ("dev", "test", "challenge")}
    blind = pd.read_csv(out / "e4_blind_key.csv").to_dict("records")
    summary.setdefault("E5_chosen_original", summary.get("E5_chosen"))
    summary.update(selective_automation(frames, gold, load_catalogue("d2"), blind, out))
    allc = pd.concat(frames["challenge"])
    summary["E7"]["errors_by_type"] = allc["errors"].dropna().loc[lambda x: x != ""].value_counts().to_dict()
    summary["reanalysed"] = time.strftime("%Y-%m-%d %H:%M:%S")
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else str(o)))
    from .report import write_markdown
    write_markdown(summary, out / "summary.md")
    print(f"Re-analysed E5/E6 from stored cases. See {out / 'summary.md'}")


# ----------------------------------------------------------------------------- main
def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default=None, help="azure | openai | fake (default: LLM_PROVIDER from .env)")
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=None, help="limit cases per set (smoke test)")
    ap.add_argument("--skip-e1", action="store_true")
    ap.add_argument("--reanalyse", action="store_true",
                    help="recompute E5/E6 from the stored per-case files of an earlier run (no LLM calls, no cost)")
    a = ap.parse_args(argv)
    if a.reanalyse:
        return reanalyse(a.provider or env("LLM_PROVIDER", "azure"))
    llm = get_llm(a.provider)
    out = ROOT / "results" / llm.name
    (out / "runs").mkdir(parents=True, exist_ok=True)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    for old in (out / "runs").glob("*.db"):
        old.unlink()
    workers = 1 if llm.is_fake else a.workers
    t0 = time.time()
    summary = {"provider": llm.name, "model": llm.chat_model, "runs": a.runs, "limit": a.limit,
               "started": time.strftime("%Y-%m-%d %H:%M:%S")}
    if not a.skip_e1:
        summary["E1"] = e1_public(llm, a.runs, workers, a.limit, out)
        plot_confusion(summary["E1"]["confusion_priority_run1"]["prototype"], PRIOS, out / "figures" / "e1_priority_confusion.png",
                       "Public dataset D1, prototype (run 1)")
    summary.update(e2_to_e7(llm, a.runs, workers, a.limit, out))
    plot_confusion(summary["E2_confusion_priority_run1"]["matrix"], PRIOS, out / "figures" / "e2_priority_confusion.png",
                   "Controlled benchmark D2, prototype (run 1)")
    summary["duration_min"] = round((time.time() - t0) / 60, 1)
    summary["usage"] = vars(llm.usage)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=lambda o: None if (isinstance(o, float) and math.isnan(o)) else str(o)))
    from .report import write_markdown
    write_markdown(summary, out / "summary.md")
    print(f"Done in {summary['duration_min']} min. See {out / 'summary.md'}")


if __name__ == "__main__":
    main()
