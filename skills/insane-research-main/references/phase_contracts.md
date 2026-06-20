# Phase Contracts

## Overview

Each research phase has defined inputs, outputs, and success criteria.

---

## Phase 1: Question Scoping

### Input
- Raw research topic from user
- User's initial requirements (if any)

### Process
1. Ask clarifying questions
2. Define scope boundaries
3. Identify constraints
4. Confirm output format

### Output
```json
{
  "topic": "refined topic statement",
  "focus_areas": ["area1", "area2"],
  "output_format": "comprehensive_report | executive_summary | modular",
  "scope": {
    "geographic": "Global | Regional",
    "temporal": "2023-2025",
    "industries": ["tech", "healthcare"],
    "exclusions": ["what to exclude"]
  },
  "sources": {
    "preferred": ["academic", "official"],
    "avoid": ["marketing materials"]
  },
  "audience": "executives | technical | general",
  "special_requirements": ["visualizations", "code examples"]
}
```

### Success Criteria
- [ ] User confirmed understanding
- [ ] Scope is bounded and clear
- [ ] Output format defined
- [ ] No ambiguity remaining

---

## Phase 2: Retrieval Planning

### Input
- Phase 1 requirements output

### Process
1. Decompose topic into subtopics
2. Generate search queries per subtopic
3. Assign agent tasks
4. Estimate timeline

### Output
```json
{
  "subtopics": [
    {
      "name": "Subtopic 1",
      "questions": ["Q1", "Q2"],
      "search_queries": ["query1", "query2"],
      "source_types": ["academic", "news"],
      "priority": 1
    }
  ],
  "agent_assignments": [
    {
      "agent": "explore",
      "subtopic": "Subtopic 1",
      "focus": "current_state"
    }
  ],
  "estimated_sources": 50,
  "estimated_time_minutes": 30
}
```

### Success Criteria
- [ ] 3-5 distinct subtopics
- [ ] No overlapping subtopics
- [ ] Search queries are specific
- [ ] User approved plan

---

## Phase 3: Iterative Querying

### Input
- Phase 2 research plan
- Agent assignment list

### Process
1. Deploy parallel agents
2. Execute searches
3. Fetch and extract content
4. Store sources with metadata

### Output
```
sources/sources.jsonl (one source per line):
{
  "id": "src_001",
  "url": "https://...",
  "title": "Source Title",
  "author": "Author Name",
  "date": "2024-01-15",
  "domain": "example.com",
  "type": "academic | news | official | blog",
  "quality_rating": "A",
  "fetched_at": "2025-01-29T12:00:00Z",
  "content_hash": "sha256...",
  "snippet": "relevant excerpt...",
  "subtopic": "Subtopic 1",
  "claims": ["claim1", "claim2"]
}
```

### Success Criteria
- [ ] Minimum sources per subtopic reached
- [ ] Source diversity (multiple domains)
- [ ] All URLs accessible
- [ ] Content successfully extracted

---

## Phase 4: Source Triangulation

### Input
- Phase 3 sources.jsonl
- Claims from each source

### Process
1. Group claims by subtopic
2. Cross-reference across sources
3. Identify contradictions
4. Rate source quality

### Output
```json
{
  "verified_claims": [
    {
      "claim": "Claim text",
      "sources": ["src_001", "src_003", "src_007"],
      "confidence": "high",
      "contradictions": []
    }
  ],
  "contradictions": [
    {
      "claim_a": "Claim version A",
      "source_a": "src_002",
      "claim_b": "Claim version B", 
      "source_b": "src_005",
      "resolution": "explanation or 'unresolved'"
    }
  ],
  "source_quality_report": {
    "A_rated": 5,
    "B_rated": 12,
    "C_rated": 8,
    "D_rated": 3,
    "E_rated": 0
  }
}
```

### Claim Ledger (필수 산출 계약)
`verified_claims`의 각 핵심 주장 레코드는 다음 필드를 포함한다:
```json
{
  "claim": "주장 텍스트",
  "status": "verified | refuted | unresolved",
  "confidence": "high | medium | low",
  "sources": ["src_001", "src_003"],
  "source_count": 2,
  "primary_source": true,
  "counter_search": "반증 검색 1회 결과 요약"
}
```
**Abstention 강제**: `source_count < 2` OR 미해소 충돌 OR (강한 주장인데 `primary_source=false`) → `status=unresolved`. unresolved/refuted 주장은 본문에서 단정 금지.

### Success Criteria
- [ ] Key claims have 2+ sources
- [ ] Contradictions documented
- [ ] No E-rated sources in final output
- [ ] Quality distribution reasonable
- [ ] 모든 핵심 주장이 status(verified/refuted/unresolved)로 분류됨
- [ ] 각 핵심 주장에 counter_search 결과 존재 (CoV 계약)
- [ ] unresolved/refuted 주장이 본문 단정에 사용되지 않음

---

## Phase 5: Knowledge Synthesis

### Input
- Phase 4 verified claims
- Phase 3 source content

### Process
1. Organize by subtopic
2. Create narrative structure
3. Write sections with citations
4. Add visualizations

### Output
```
artifacts/drafts/
├── draft_executive_summary.md
├── draft_subtopic_1.md
├── draft_subtopic_2.md
├── draft_subtopic_3.md
└── draft_conclusion.md
```

Each draft includes:
- Section heading hierarchy
- Inline citations for all claims
- Data tables where relevant
- Visualization placeholders

### Success Criteria
- [ ] All subtopics covered
- [ ] Every claim cited
- [ ] Logical flow between sections
- [ ] Draft readable standalone

---

## Phase 6: Quality Assurance

### Input
- Phase 5 draft documents
- Phase 4 verification data

### Process
1. Citation verification
2. Hallucination check
3. Completeness review
4. Format consistency

### Output
```json
{
  "qa_passed": true,
  "issues_found": [
    {
      "type": "missing_citation",
      "location": "section 2, paragraph 3",
      "severity": "high",
      "resolved": true
    }
  ],
  "citation_stats": {
    "total_citations": 85,
    "verified": 85,
    "broken_links": 0
  },
  "completeness": {
    "subtopics_covered": "5/5",
    "requirements_met": "8/8"
  }
}
```

### Success Criteria
- [ ] All citations verified
- [ ] No hallucinations detected
- [ ] All requirements addressed
- [ ] Format consistent throughout

---

## Phase 7: Output & Packaging

### Input
- Phase 6 verified drafts
- Original requirements

### Process
1. Apply output templates
2. Generate table of contents
3. Create bibliography
4. Package final deliverables

### Output
```
outputs/
├── 00_executive_summary.md
├── 01_full_report/
│   ├── 00_table_of_contents.md
│   ├── 01_introduction.md
│   ├── 02_subtopic_1.md
│   ├── ...
│   └── 99_conclusion.md
├── 02_end_user_guide/      (if requested)
├── 03_developer_blueprint/ (if requested)
├── 04_appendices/
│   ├── bibliography.md
│   ├── glossary.md
│   └── methodology.md
└── comparison_data.json    (for website generation)

sources/
└── bibliography.md         (formatted citations)
```

### Success Criteria
- [ ] All requested outputs generated
- [ ] Bibliography complete
- [ ] Table of contents accurate
- [ ] Files properly named and organized

---

## State Transitions

```
INIT → PHASE_1_SCOPING → PHASE_2_PLANNING → PHASE_3_QUERYING
                                                    ↓
COMPLETED ← PHASE_7_OUTPUT ← PHASE_6_QA ← PHASE_5_SYNTHESIS ← PHASE_4_TRIANGULATION
```

### Transition Rules
- Each phase must complete before next starts
- Failed phase can be retried
- Phase 3-5 may loop (iterative refinement)
- Phase 6 failure returns to Phase 5

### Resume Points
- Session can resume from any incomplete phase
- State preserved in state.json
- Artifacts saved per phase
