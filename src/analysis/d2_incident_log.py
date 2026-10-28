"""Problem analysis of the public ServiceNow incident log D2 (Amaral et al. 2018, UCI, CC BY 4.0).

Uses the last recorded event of each incident and writes summary indicators to results/d2_summary.json.
"""
import json, sys
from pathlib import Path
import pandas as pd

RAW = Path(sys.argv[1] if len(sys.argv) > 1 else "data/raw/incident_event_log.csv")
OUT = Path("results/d2_summary.json")

df = pd.read_csv(RAW)
last = df.sort_values(["number", "sys_mod_count"]).groupby("number").tail(1)
n = len(last)
res = {
    "events": int(len(df)),
    "incidents": int(n),
    "priority_share": {k: round(v, 4) for k, v in last["priority"].value_counts(normalize=True).sort_index().items()},
    "impact_share": {k: round(v, 4) for k, v in last["impact"].value_counts(normalize=True).sort_index().items()},
    "urgency_share": {k: round(v, 4) for k, v in last["urgency"].value_counts(normalize=True).sort_index().items()},
    "reassigned_at_least_once": round(float((last["reassignment_count"] > 0).mean()), 4),
    "mean_reassignments_if_reassigned": round(float(last.loc[last["reassignment_count"] > 0, "reassignment_count"].mean()), 2),
    "reassigned_3_or_more": round(float((last["reassignment_count"] >= 3).mean()), 4),
    "assignment_groups": int(last["assignment_group"].nunique()),
    "made_sla": round(float(last["made_sla"].astype(str).str.lower().eq("true").mean()), 4),
    "priority_confirmed": round(float(last["u_priority_confirmation"].astype(str).str.lower().eq("true").mean()), 4),
    "reopened_at_least_once": round(float((last["reopen_count"] > 0).mean()), 4),
}
# mean reassignments by priority
res["mean_reassignments_by_priority"] = {k: round(v, 2) for k, v in last.groupby("priority")["reassignment_count"].mean().items()}
OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(res, indent=2, ensure_ascii=False))
print(json.dumps(res, indent=2, ensure_ascii=False))
