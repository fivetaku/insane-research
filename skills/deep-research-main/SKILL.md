---
name: deep-research-main
description: This skill should be used when a user requests deep research on any topic. Example queries include "/deep-research", "deep research on", "리서치해줘", "딥리서치", "심층 연구", "[주제]에 대해 리서치해줘".
---

# Deep Research Skill

> AI-powered comprehensive research with state management, multi-agent source verification, and structured outputs.

## Trigger Conditions

```
# Primary triggers
- "/deep-research [topic]"
- "/research [topic]"
- "딥리서치 [주제]"
- "심층 연구 [주제]"
- "[주제]에 대해 리서치해줘"
- "[주제] 리서치"
- "deep research on [topic]"

# Resume triggers
- "/deep-research resume [session_id]"
- "/research-resume [session_id]"

# Status triggers
- "/deep-research status"
- "/research-status"
```

---

## WHEN TRIGGERED - EXECUTE IMMEDIATELY

**DO NOT just display this documentation. EXECUTE the research flow immediately.**

### On Trigger Action:

1. **Extract the topic** from user's message
2. **Start Phase 1** - Use `AskUserQuestion` tool for interactive selection

---

## CRITICAL REQUIREMENT

**CALL THE `AskUserQuestion` TOOL IMMEDIATELY.**

DO NOT output text-based questions. INSTEAD, call the AskUserQuestion tool with JSON parameters.

---

### Language Detection
- Detect the language of user's input (topic query)
- Generate ALL question labels and descriptions in the SAME LANGUAGE as user input
- If Korean -> Korean options, If English -> English options, etc.

**EXECUTE:** 아래 JSON으로 AskUserQuestion 도구를 즉시 호출한다 (combine into 1-4 question groups).
Translate all labels/descriptions to match user's language:

**English Example:**
```json
{
  "questions": [
    {
      "question": "What aspects interest you most?",
      "header": "Focus",
      "options": [
        {"label": "Current state & trends", "description": "Latest developments, market status, key players"},
        {"label": "Technical deep-dive", "description": "Architecture, implementation, tech stack"},
        {"label": "Market analysis", "description": "Market size, growth rate, competition"},
        {"label": "All of the above (Recommended)", "description": "Comprehensive research - all aspects"}
      ],
      "multiSelect": false
    },
    {
      "question": "What type of deliverable do you want?",
      "header": "Output",
      "options": [
        {"label": "Comprehensive report (Recommended)", "description": "20-50+ pages, detailed analysis and insights"},
        {"label": "Executive summary", "description": "3-5 pages, key points only"},
        {"label": "Modular documents", "description": "Multiple documents by topic"}
      ],
      "multiSelect": false
    },
    {
      "question": "Who will read this research?",
      "header": "Audience",
      "options": [
        {"label": "Technical team/Developers", "description": "Include technical details"},
        {"label": "Business executives", "description": "Focus on strategic insights"},
        {"label": "Researchers/Academic", "description": "Academic citations and methodology"},
        {"label": "General audience", "description": "Easy explanations and overview"}
      ],
      "multiSelect": false
    },
    {
      "question": "Any source preferences?",
      "header": "Sources",
      "options": [
        {"label": "Academic/Papers", "description": "Peer-reviewed papers, conferences"},
        {"label": "Industry reports", "description": "Gartner, white papers, analyst reports"},
        {"label": "News/Current", "description": "Media, blogs, latest announcements"},
        {"label": "All sources (Recommended)", "description": "All reliable sources"}
      ],
      "multiSelect": false
    }
  ]
}
```

**Korean Example (EXECUTE):**
```json
{
  "questions": [
    {
      "question": "어떤 측면에 관심이 있으신가요?",
      "header": "Focus",
      "options": [
        {"label": "현재 상태와 트렌드", "description": "최신 동향, 시장 현황, 주요 플레이어"},
        {"label": "기술 심층 분석", "description": "아키텍처, 구현 방법, 기술 스택"},
        {"label": "시장 분석", "description": "시장 규모, 성장률, 경쟁 구도"},
        {"label": "모두 포함 (Recommended)", "description": "종합 리서치 - 모든 측면 분석"}
      ],
      "multiSelect": false
    }
  ]
}
```

3. **After user responds**:
   - Create session folder: `RESEARCH/{topic}_{timestamp}/`
   - Initialize `state.json`
   - Execute Phase 2-7 sequentially
   - Use parallel background agents for searching
   - Deliver final report to `outputs/` folder

---

## The 7-Phase Deep Research Process

### Phase 1: Question Scoping
- Clarify the research question with the user
- Define output format and success criteria
- Identify constraints and desired tone
- Create unambiguous query with clear parameters

### Phase 2: Retrieval Planning
- Break main question into 3-5 subtopics
- Generate specific search queries per subtopic
- Select appropriate data sources
- Create research plan for user approval
- Use Graph of Thoughts to model research as operations

---

## DATE-AWARE QUERY GENERATION (CRITICAL)

**All search queries MUST include current date context for freshness.**

### Get Today's Date First
Before generating ANY search query, determine today's date from the system context.

### Query Generation Rules

1. **Always append year to queries:**
   - BAD: "AI code assistants market"
   - GOOD: "AI code assistants market 2026"
   - GOOD: "AI code assistants trends February 2026"

2. **Use recency operators:**
   - "after:2025" for Google
   - "since:2025" for news
   - "2025..2026" for date ranges

3. **Add freshness keywords:**
   - "latest", "recent", "current", "new"
   - "[current year] update"

4. **Example transformations:**
   | User Query | Generated Search Query |
   |------------|----------------------|
   | AI 코딩 어시스턴트 | AI 코딩 어시스턴트 2026 최신 동향 |
   | startup trends | startup trends 2026 latest |
   | React vs Vue | React vs Vue 2026 comparison |

5. **For academic/historical research:**
   - Still include current year for "state of" queries
   - Use date ranges: "climate change research 2020-2026"

### Search Query Template
```
[topic] [current_year] [freshness_keyword] [specific_aspect]
```

---

### Phase 3: Iterative Querying
- Execute searches systematically with parallel agents
- Navigate and extract relevant information
  - WebFetch 실패 시 → `tool_strategy.md`의 플랫폼별 접근 전략 또는 Fallback 순서대로 시도
  - 우회 성공 시 소스 신뢰도에 `via_fallback` 태그 추가
  - 실패한 URL과 우회 시도 결과를 `sources/failed_urls.txt`에 함께 기록
- Formulate new queries based on findings
- Use multiple search modalities (web, academic, code)

### Phase 4: Source Triangulation
- Compare findings across multiple sources
- Validate claims with cross-references (minimum 2 sources for key claims)
- Handle inconsistencies and note contradictions
- Assess source credibility with A-E ratings

### Phase 5: Knowledge Synthesis
- Structure content logically
- Write comprehensive sections
- Include inline citations for EVERY claim
- Add data visualizations when relevant

### Phase 6: Quality Assurance
- Check for hallucinations and errors
- Verify all citations match content
- Ensure completeness and clarity
- Apply Chain-of-Verification techniques

### Phase 7: Output & Packaging
- Format for optimal readability
- Include executive summary
- Create proper bibliography
- Export in requested format
- Optionally generate interactive website

---

## Multi-Agent Research Strategy

### Agent Deployment (Phase 3)

Deploy 3-5 parallel agents to maximize coverage:

| Agent Type | Count | Focus | Output |
|------------|-------|-------|--------|
| Web Research | 2-3 | Current info, trends, news | Structured summaries with source URLs |
| Academic/Technical | 1-2 | Papers, specs, methodology | Technical analysis with citations |
| Cross-Reference | 1 | Fact-checking, verification | Confidence ratings for key findings |

Launch multiple Task calls in a single response for parallel execution with `mode: "bypassPermissions"`. Each agent receives a focused prompt with specific subtopic and citation requirements.

For detailed agent prompt templates and Graph of Thoughts integration:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/agent_prompts.md`

---

## Tool Usage

기본 도구(WebSearch, WebFetch, Bash/curl)로 리서치를 수행한다. 플랫폼별 최적 접근법은 tool_strategy.md를 참조한다.
환경에 MCP 도구(Perplexity, Firecrawl, Exa 등)가 설치되어 있으면 우선 활용하되, 없어도 기본 도구만으로 충분한 리서치가 가능하다.

Deploy parallel research agents using the Task tool with `run_in_background=True` and `mode: "bypassPermissions"` for concurrent subtopic investigation.

For detailed tool strategy and code examples:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/tool_strategy.md`

---

## Citation Requirements

Every factual claim MUST include inline citation.

### Mandatory Standards

1. **Author/Organization** - Who made this claim
2. **Date** - When published
3. **Source Title** - Name of paper, article, or report
4. **URL/DOI** - Direct link to verify
5. **Page Numbers** - For lengthy documents (when applicable)

### Source Quality Ratings

| Grade | Description | Examples |
|-------|-------------|----------|
| **A** | Peer-reviewed, systematic reviews, meta-analyses | Nature, Lancet, IEEE |
| **B** | Official docs, clinical guidelines, cohort studies | FDA, W3C, WHO |
| **C** | Expert opinion, case reports, industry reports | Gartner, conferences |
| **D** | Preliminary research, preprints, white papers | arXiv, company blogs |
| **E** | Anecdotal, theoretical, speculative | Social media, forums |

### Red Flags (Unreliable Sources)
- No author attribution
- Missing publication dates
- Broken or suspicious URLs
- Claims without data
- Conflicts of interest not disclosed
- Predatory journals
- Retracted papers

For detailed citation formatting rules, refer to:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/citation_rules.md`

For complete source quality assessment rubric:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/quality_rubric.md`

---

## Hallucination Prevention

### Core Strategies

1. **Always ground statements in source material**
   - Never claim without a verifiable source
   - If uncertain, state "Source needed" rather than guessing

2. **Use Chain-of-Verification for critical claims**
   - Generate verification questions
   - Search for answers independently
   - Only finalize when verified

3. **Cross-reference multiple sources**
   - Key findings need 2+ independent sources
   - Note when sources disagree

4. **Explicitly state uncertainty**
   - "According to [source]..." not "Studies show..."
   - Qualify preliminary or contested findings

### Verification Checklist
- [ ] Every claim has inline citation
- [ ] All URLs are accessible
- [ ] No orphan citations
- [ ] Contradictions acknowledged
- [ ] Source quality ratings applied

---

## State Management

### state.json Schema

```json
{
  "session_id": "Topic_Name_20260224_143000",
  "topic": "Research Topic",
  "created_at": "2026-02-24T14:30:00Z",
  "updated_at": "2026-02-24T15:45:00Z",
  "status": "PHASE_3_QUERYING",
  "current_phase": 3,
  "requirements": {
    "focus": ["aspect1", "aspect2"],
    "output_format": "comprehensive_report",
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

### sources.jsonl Schema (one JSON per line)
```json
{"id": "src_001", "url": "https://...", "title": "Article Title", "author": "Author", "date": "2024-06-15", "domain": "nature.com", "type": "academic", "quality_rating": "A", "snippet": "relevant excerpt...", "claims": ["claim1"], "verified": true}
```

For detailed phase input/output contracts:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/phase_contracts.md`

---

## Output Structure

```
RESEARCH/{topic}_{timestamp}/
├── state.json                    # Session state (resumable)
├── README.md                     # Navigation guide
│
├── artifacts/                    # Intermediate outputs
│   ├── research_plan.json
│   ├── agent_results/
│   └── drafts/
│
├── sources/
│   ├── sources.jsonl            # All collected sources
│   ├── bibliography.md          # Formatted citations
│   └── quality_report.md        # Source quality ratings
│
├── outputs/                     # FINAL DELIVERABLES
│   ├── 00_executive_summary.md
│   ├── 01_full_report/
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

### Output Templates

Use the templates at `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/assets/templates/` for consistent formatting:

| Template | Purpose |
|----------|---------|
| `executive_summary.md` | Executive summary structure |
| `full_report_section.md` | Individual report section template |
| `bibliography.md` | Bibliography with quality distribution |
| `readme_research.md` | Research session README/navigation |
| `website_template.html` | Interactive web presentation |

---

### Research Type 기반 골격 동적 생성 (참고용 — 기본 5섹션은 그대로 유지)

기본 5섹션 골격(introduction/landscape/challenges/future_outlook/conclusions)이 모든 리서치의 default. 사용자가 명시적으로 다른 type을 요청한 경우, 아래 **참고 예시 패턴**을 보고 사용자 리서치에 맞게 골격을 **즉석 동적 생성**한다.

> **주의**: 기본 7-Phase + 5섹션 + Date-aware는 모두 deep-research의 핵심 contract로 보존. 본 type별 골격은 **사용자 명시 요청 시에만** 적용되는 advanced 옵션이며, 표는 카탈로그 메뉴가 아니라 **동적 생성 학습용 예시**다.

#### 동적 생성 원칙

- 사용자 리서치 핵심 → **5 섹션 슬롯 채우기**: 도입(introduction) / 핵심 분석 / 비교/예측/원인 등 도메인 특화 / 한계와 위험 / 결론
- 같은 type이라도 사용자 주제에 따라 섹션 명을 다르게 (단순 카피 금지)
- 표의 섹션 명은 **그대로 사용하지 말고**, 사용자 주제에 맞는 명칭으로 변환

#### 참고 예시 (메뉴 아님 — 패턴 학습용)

| Research Type | 5섹션 패턴 예시 | 적합 사례 |
|---|---|---|
| **Exploratory** (새 영역 탐색) | introduction / landscape / opportunities / challenges / conclusions | 신규 시장/기술 탐색 |
| **Comparative** (A vs B 비교) | introduction / criteria / comparison_matrix / recommendation / conclusions | 도구/제품 비교 |
| **Predictive** (미래 시나리오) | introduction / current_state / trends / scenarios / risks_and_recommendations | 시장 예측 / 기술 로드맵 |
| **Analytical** (원인-결과) | introduction / problem / causes / effects / conclusions | 사건 분석 / 인과 추적 |
| **기본 (Generic)** | introduction / current_landscape / challenges / future_outlook / conclusions | 종합 리서치 (default) |

→ 위는 **패턴 학습용 예시**. 사용자 주제가 "X 시장의 한국 vs 일본 차이"면 Comparative 패턴으로 `introduction / 시장규모비교 / 사용자행동차이 / 규제차이 / 진입전략추천` 같이 섹션 명을 즉석 변환.

#### 적용 절차

1. Phase 1 (Question Scoping)에서 사용자 자연어로부터 리서치 type 추정 (Exploratory / Comparative / Predictive / Analytical / Generic 패턴 중 가장 가까운 것)
2. 위 예시 패턴을 학습한 후, **사용자 주제에 맞춰 5 섹션 명을 동적 생성**
3. 사용자에게 confirm: "이 리서치는 [Comparative] 패턴에 가까워 보입니다. 5섹션을 [introduction / X 비교 기준 / X vs Y 비교 / 추천 / 결론]으로 진행할까요? 또는 기본 5섹션으로?"
4. 사용자 confirm → 동적 생성된 골격 사용 / 사용자 미명시 또는 모호 → **기본 5섹션 사용 (안전 default)**
5. state.json `report_skeleton` 필드에 최종 결정된 골격 기록 (resume 가능)

#### ⚠️ 주의사항

- type 자동 결정 금지 — 사용자 confirm 필수
- 위 표는 메뉴가 아닌 **패턴 학습용 예시** — 섹션 명을 그대로 카피하지 말고 사용자 주제에 맞춰 변환
- 7-Phase / minimum 2 sources / A-E quality / Hallucination Prevention 등 결정 contract는 모두 그대로 유지
- 본 골격 동적 생성은 advanced 옵션이며, 기본 동작은 5섹션 그대로
- 새 type 사례를 본 표에 추가하지 말 것 — 이 표는 카탈로그가 아닌 패턴 예시집

---

## Structured Query Support

For precise research control, accept structured JSON queries following the schema at:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/query_schema.json`

When a user provides a JSON object as input, parse it according to the schema and skip Phase 1 (Question Scoping) since requirements are already defined.

Example queries are available at:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/examples/`

---

## Resume Protocol

When resume is triggered:

1. List available sessions: `RESEARCH/*/state.json`
2. Load selected session's `state.json`
3. Check `progress` object for last completed phase
4. Resume from next pending phase
5. Continue execution loop

```python
for phase_num in range(1, 8):
    phase_key = f"phase_{phase_num}"
    if state["progress"][phase_key] == "in_progress":
        resume_phase(phase_num)
        break
    elif state["progress"][phase_key] == "pending":
        start_phase(phase_num)
        break
```

---

## Error Handling

### Phase Failures
1. Log error to `state.json` errors array
2. Mark phase as `failed` in progress
3. Notify user with details
4. Offer: Retry / Skip / Abort

### Network Failures
- Retry up to 3 times with backoff
- If still failing → tool_strategy.md의 "접근 불가 시 우회 전략 (Fallback)" 참조
  - 모바일 UA curl → OGP 메타태그 → Google 캐시/Wayback → curl_cffi → Playwright MCP
- 응답 검증 규칙으로 성공/실패 판정 (로그인 페이지, CAPTCHA, 빈 SPA 감지)
- Log failed URLs + fallback attempt results to `sources/failed_urls.txt`
- Continue with available sources (including fallback-retrieved content)

### Token Limits
- Split long documents into chunks
- Save intermediate results frequently
- Use summarization for very long sources

---

## Quality Checklist (Before Completion)

- [ ] Every claim has a verifiable source
- [ ] Multiple sources corroborate key findings
- [ ] Contradictions are acknowledged and explained
- [ ] Sources are recent and authoritative
- [ ] No hallucinations or unsupported claims
- [ ] Clear logical flow from evidence to conclusions
- [ ] Proper citation format throughout
- [ ] Executive summary reflects full content
- [ ] Bibliography is complete
- [ ] All background agents completed and results collected

---

## Scripts and Utilities

State management scripts are available at:
`${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/scripts/`

| Script | Purpose |
|--------|---------|
| `orchestrator.py` | Research state machine controller - session creation, phase management, source tracking |
| `pipelines.py` | Pipeline definitions - agent prompts, clarification templates, synthesis prompts |

These can be executed via Bash to initialize sessions or manage state programmatically.

---

## References

For detailed documentation on specific aspects:

| Reference | Location |
|-----------|----------|
| Citation formatting rules | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/citation_rules.md` |
| Phase input/output contracts | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/phase_contracts.md` |
| Source quality rubric | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/quality_rubric.md` |
| Agent prompt templates & GoT | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/agent_prompts.md` |
| Tool strategy & code examples | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/tool_strategy.md` |
| Structured query schema | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/query_schema.json` |
| Query generation guide | `${CLAUDE_PLUGIN_ROOT}/skills/deep-research-main/references/query_generator.md` |
