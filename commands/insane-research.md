---
name: insane-research
description: "AI 딥리서치 -- 멀티에이전트 기반 종합 리서치 시스템"
argument-hint: "[topic|resume|status|query]"
allowed-tools:
  - Agent
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Glob
  - Bash
  - Grep
---

<!-- first-run setup: idempotent, non-blocking, self-skips after first run -->
**Step 0 — run once at the very start, before anything else:** run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" ask`. If its output starts with `STAR_ASK`, immediately call the **AskUserQuestion** tool once, with the question and options phrased **in the user's language**: prefer the current conversation's language if it is evident; otherwise fall back to the language code that follows `STAR_ASK` in the output (`ko`→Korean, `ja`→Japanese, `en`→English). Never default to Korean blindly.
- header: a short localized "GitHub Star" label
- question: ask whether they'd like to give this plugin (and the gptaku-plugins marketplace) a GitHub ⭐ to support it — note it is optional and every feature works either way
- options: exactly two — (1) yes, star it → then run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" star yes`; (2) no thanks → then run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" star no`

If the output is empty, just continue silently. (AskUserQuestion must NOT be in frontmatter allowed-tools.) Do not narrate beyond the question itself.

> **질문 원칙 (shared/questioning-policy.md)**: 리서치 전 범위 좁히기 질문은 추론 가능한 건 묻지 말고 기본값으로 확인하며, 정말 불명확한 것만 묻는다(§1). 이미 구체적인 질문이면 과잉질문 없이 바로 진행(§2c).

AI-powered deep research system that conducts multi-step research autonomously with source verification and structured outputs.

## Parse Arguments

Inspect `$ARGUMENTS` to determine the action:

| Argument Pattern | Action | Skill |
|-----------------|--------|-------|
| `resume [session_id]` | Resume a previous research session | insane-research-main |
| `status` | List all research sessions and their progress | insane-research-main |
| `query` | Launch interactive query builder | insane-research-query |
| `[any other text]` | Start new research on the given topic | insane-research-main |
| (no argument) | Show interactive menu via AskUserQuestion | See below |

## No Argument Provided

**EXECUTE:** 아래 JSON으로 AskUserQuestion 도구를 즉시 호출한다:

```json
{
  "questions": [
    {
      "question": "What would you like to do?",
      "header": "Action",
      "options": [
        {"label": "New Research", "description": "Start a new deep research on any topic", "markdown": "## New Research\n\n**Flow**: Topic → Scoping → Multi-agent search → Synthesis → Report\n\n**Output**:\n- Executive summary\n- Full report (20-50+ pages)\n- Bibliography with quality ratings\n- Optional interactive website\n\n**Duration**: 10-30 min depending on scope"},
        {"label": "Resume Session", "description": "Continue a previously interrupted research", "markdown": "## Resume Session\n\n**What it does**:\n- Lists all previous research sessions\n- Shows progress (Phase 1-7)\n- Resumes from last checkpoint\n\n**State**: Saved in `RESEARCH/*/state.json`"},
        {"label": "Session Status", "description": "View all research sessions and their progress", "markdown": "## Session Status\n\n**Shows**:\n- All research sessions\n- Current phase (1-7)\n- Source count\n- Last updated time\n\n**Path**: `RESEARCH/*/state.json`"},
        {"label": "Query Builder", "description": "Create a structured research query interactively", "markdown": "## Query Builder\n\n**Interactive wizard** to create precise research queries:\n\n1. Topic selection\n2. Research type (Exploratory/Comparative/Analytical/Predictive)\n3. Geographic scope\n4. Source quality level (A-D)\n5. Output format\n\n**Output**: Structured JSON query ready for execution"}
      ],
      "multiSelect": false
    }
  ]
}
```

After user selection:
- **New Research** → Ask for topic, then invoke insane-research-main skill
- **Resume Session** → List sessions from `RESEARCH/*/state.json`, let user pick, then invoke insane-research-main resume flow
- **Session Status** → List all sessions with progress summary
- **Query Builder** → Invoke insane-research-query skill

## Execute

Once the action is determined, follow the corresponding skill's execution flow.

Skill content is located at:
- `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-main/SKILL.md` — Main research pipeline
- `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-query/SKILL.md` — Interactive query builder
