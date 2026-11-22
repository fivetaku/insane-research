# Session layout — state.json, output tree, templates, resume loop

Referenced from SKILL.md "State Management", "Output Structure" and "Resume Protocol".

## state.json schema

```json
{
  "session_id": "Topic_Name_20260224_143000",
  "ledger_schema": 2,
  "topic": "Research Topic",
  "created_at": "2026-02-24T14:30:00Z",
  "updated_at": "2026-02-24T15:45:00Z",
  "status": "PHASE_3_QUERYING",
  "current_phase": 3,
  "requirements": {
    "focus": ["aspect1", "aspect2"],
    "output_format": "brief | executive_summary | comprehensive_report | modular",
    "scope": {"timeframe": {}, "geography": {}},
    "sources": {"required_types": [], "min_quality": "B"},
    "audience": "executive",
    "special_requirements": []
  },
  "plan": {
    "subtopics": [],
    "search_queries": {},
    "agent_assignments": []
  },
  "progress": {
    "phase_1": "completed",
    "phase_2": "completed",
    "phase_3": "in_progress",
    "phase_4": "pending",
    "phase_5": "pending",
    "phase_6": "pending",
    "phase_7": "pending"
  },
  "sources_count": 0,
  "artifacts": {},
  "errors": []
}
```

Optional fields written later: `exec_mode` (Phase 3), `report_skeleton` (see `skeleton_patterns.md`),
`verification` (validate_ledger.py), `report_verification` (verify_report.py).

## Output tree

```
RESEARCH/{topic}_{timestamp}/
├── state.json                    # Session state (resumable)
├── README.md                     # Navigation guide
│
├── artifacts/                    # Intermediate outputs
│   ├── research_plan.json
│   ├── claim_ledger.jsonl        # Phase 4 ledger (gate input)
│   ├── expansion_log.md          # EXPAND lead log
│   ├── agent_results/
│   └── drafts/
│
├── sources/
│   ├── sources.jsonl            # All collected sources
│   ├── snapshots/               # snapshot_sources.py output (gate evidence)
│   ├── failed_urls.txt
│   ├── bibliography.md          # Formatted citations
│   └── quality_report.md        # Source quality ratings
│
├── outputs/                     # FINAL DELIVERABLES
│   ├── verified_claims.json / unresolved_claims.json / refuted_claims.json
│   ├── eval_report.json
│   ├── 00_executive_summary.md
│   ├── 01_full_report/          # long-form option only
│   │   ├── 01_introduction.md
│   │   ├── 02_current_landscape.md
│   │   ├── 03_challenges.md
│   │   ├── 04_future_outlook.md
│   │   └── 05_conclusions.md
│   ├── 02_appendices/
│   └── comparison_data.json
│
└── website/                     # (optional) Visual presentation
    ├── index.html
    ├── styles.css
    └── script.js
```

For a brief (the default), `00_executive_summary.md` (or a single `report.md`) is the whole deliverable;
the `01_full_report/` split is used only when the user chose the long form.

## Output templates

Templates live at `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-main/assets/templates/`:

| Template | Purpose |
|----------|---------|
| `executive_summary.md` | Executive summary structure |
| `full_report_section.md` | Individual report section template |
| `bibliography.md` | Bibliography with quality distribution |
| `readme_research.md` | Research session README/navigation |
| `website_template.html` | Interactive web presentation |

## Resume loop (reference implementation)

```python
for phase_num in range(1, 8):
    phase_key = f"phase_{phase_num}"
    if state["progress"][phase_key] in ("failed", "in_progress"):
        resume_phase(phase_num)
        break
    elif state["progress"][phase_key] == "pending":
        start_phase(phase_num)
        break
```
