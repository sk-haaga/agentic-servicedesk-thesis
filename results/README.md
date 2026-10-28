# Results

Each evaluation run writes to its own folder `<provider>_YYYY-MM-DD-HH-MM` (start time, local clock), so a
new run never overwrites an earlier one. Re-analyses write `summary_reanalysed.json/.md` into the folder
they analyse and leave the original files unchanged.

| Folder | What it is |
|---|---|
| `azure_2026-10-14-23-58` | First complete evaluation (design iteration 1). Contains the threshold-selection defect described in the thesis. |
| `azure_2026-10-15-15-19` | Evaluation of design iteration 1 after the defect was corrected (the results reported in the first thesis draft). |

Naming in the two iteration-1 folders: they were produced before the data sets were renumbered, so the
controlled benchmark appears there as **d2** (`d2_*_cases.jsonl`, "D2" in `summary.md`). In the thesis and in
all later folders the controlled benchmark is **D3** and the public incident log is **D2**.

Files directly in `results/`: `d1_preparation.json` (D1 split), `d2_summary.json` (incident-log analysis,
D2) and `d3_build.json` (benchmark statistics, D3).
