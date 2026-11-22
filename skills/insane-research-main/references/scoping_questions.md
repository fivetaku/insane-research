# Phase 1 scoping questions (AskUserQuestion payloads)

Used only when SKILL.md "스코핑 우선순위" rule 2 applies (natural-language input with the focus,
deliverable and audience all unclear). Ask once, as an AskUserQuestion tool call — never as plain text.
Combine into 1-4 question groups and translate every label/description into the user's language.

## Language detection
- Detect the language of the user's topic query.
- Generate ALL question labels and descriptions in that same language (Korean input → Korean options, etc.).

## English example

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
        {"label": "Answer-sized brief (Recommended)", "description": "Conclusion first, length proportional to the question"},
        {"label": "Executive summary", "description": "3-5 pages, key points only"},
        {"label": "Comprehensive report", "description": "Long-form full report with appendices"},
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

## Korean example

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
    },
    {
      "question": "어떤 형태의 결과물을 원하시나요?",
      "header": "Output",
      "options": [
        {"label": "질문 크기에 맞춘 요약 (Recommended)", "description": "결론 먼저, 질문 범위에 비례한 분량"},
        {"label": "핵심 요약", "description": "3-5쪽, 요점만"},
        {"label": "종합 보고서", "description": "부록까지 포함한 장문 보고서"}
      ],
      "multiSelect": false
    }
  ]
}
```

## After the user responds
- Create the session folder `RESEARCH/{topic}_{timestamp}/` and initialize `state.json`
  (schema: `session_layout.md`), recording the chosen output length in `requirements.output_format`.
- Continue with Phase 2-7 as described in SKILL.md.
