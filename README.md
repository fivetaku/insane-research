English | [한국어](README.ko.md)

# insane-research

> **insane-research — AI-powered multi-agent deep research with source verification and structured outputs.**

Turn a single question into a comprehensive, citation-backed research report — automatically.

[Quick Start](#quick-start) • [Why insane-research?](#why-insane-research) • [How it works](#how-it-works) • [Commands](#commands) • [Output](#output-structure) • [Requirements](#requirements)

---

## Quick Start

### 1. Add the marketplace (once)

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. Install the plugin

```
/plugin install insane-research
```

### 3. Restart Claude Code

Cache loads on startup — a restart is required after install.

### 4. Start researching

```
/insane-research AI coding assistants productivity impact
```

Claude will ask a few scoping questions, then deploy parallel research agents and deliver a structured report.

---

## Why insane-research?

- **Parallel agents, not sequential searches** — 3-5 agents run simultaneously across web, academic, and technical sources, cutting research time significantly
- **Source quality ratings (A–E)** — Every source is graded from peer-reviewed papers (A) to speculative posts (E), so you always know what you're reading
- **Hallucination-resistant** — Every factual claim requires an inline citation; key claims are cross-verified against at least 2 independent sources
- **Resumable sessions** — Research state is saved to `state.json`; pick up where you left off if a session is interrupted
- **Complete deliverables** — Executive summary, full sectioned report, bibliography, and an optional interactive website — all generated automatically

---

## How it works

```
User query
    │
    ▼
Phase 1: Question Scoping
  └─ AskUserQuestion → focus, depth, audience, sources
    │
    ▼
Phase 2: Retrieval Planning
  └─ Break into 3-5 subtopics → search query generation → plan approval
    │
    ▼
Phase 3: Iterative Querying  ←──────────────────┐
  ├─ Web Research Agent (x2-3)                  │
  ├─ Academic/Technical Agent (x1-2)            │ refine if gaps
  └─ Cross-Reference Agent (x1)                 │
    │                                            │
    ▼                                            │
Phase 4: Source Triangulation ─────────────────-┘
  └─ Cross-verify key claims (≥2 sources) → A–E quality rating
    │
    ▼
Phase 5: Knowledge Synthesis
  └─ Structure → write sections → inline citations
    │
    ▼
Phase 6: Quality Assurance
  └─ Hallucination check → citation verification → completeness
    │
    ▼
Phase 7: Output & Packaging
  └─ Executive summary + full report + bibliography + website (optional)
```

---

## Commands

| Command | Description |
|---------|-------------|
| `/insane-research [topic]` | Start a new research session |
| `/insane-research resume [session_id]` | Resume a previous session |
| `/insane-research status` | View all session progress |
| `/insane-research query` | Launch the structured query builder |
| `/insane-research` | Open the interactive menu |

### Natural language triggers

```
deep research on [topic]
research [topic]
[topic] 리서치해줘
딥리서치 [주제]
심층 연구 [주제]
```

---

## Agents

Three agent types run in parallel during Phase 3:

| Agent | Count | Focus |
|-------|-------|-------|
| Web Research | 2–3 | Latest news, trends, market data |
| Academic / Technical | 1–2 | Papers, specs, official docs |
| Cross-Reference | 1 | Fact-checking key claims |

---

## Source Quality Ratings

| Grade | Type | Examples |
|-------|------|---------|
| **A** | Peer-reviewed, systematic reviews | Nature, Lancet, IEEE |
| **B** | Official docs, clinical guidelines | FDA, W3C, WHO |
| **C** | Expert opinion, industry reports | Gartner, conferences |
| **D** | Preprints, white papers | arXiv, company blogs |
| **E** | Anecdotal, speculative | Social media, forums |

---

## Output Structure

```
RESEARCH/{topic}_{timestamp}/
├── state.json                    # Session state (for resume)
├── README.md                     # Navigation guide
├── outputs/
│   ├── 00_executive_summary.md   # 3–5 page summary
│   ├── 01_full_report/           # Full sectioned report
│   ├── 02_appendices/            # Supporting material
│   └── comparison_data.json      # Structured comparison data
├── sources/
│   ├── sources.jsonl             # Collected sources
│   ├── bibliography.md           # Formatted bibliography
│   └── quality_report.md         # Source quality ratings
└── website/                      # (optional) Interactive presentation
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## Requirements

- [Claude Code](https://docs.anthropic.com/claude-code) CLI
- WebSearch (built-in) or a web search MCP server

### Optional MCP servers (enhance search coverage)

- Firecrawl
- Google Search MCP
- Exa Search

---

## License

MIT

---

<div align="center">

**Research that cites its sources. Every time.**

</div>
