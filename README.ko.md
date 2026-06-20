[English](README.md) | 한국어

# insane-research

> **insane-research — 멀티에이전트 소스 검증과 구조화된 산출물을 갖춘 AI 리서치 시스템.**

질문 하나로 인용 출처가 검증된 종합 리서치 리포트를 자동으로 생성합니다.

[빠른 시작](#빠른-시작) • [왜 insane-research인가?](#왜-insane-research인가) • [동작 방식](#동작-방식) • [커맨드](#커맨드) • [산출물](#산출물-구조) • [요구사항](#요구사항)

---

## 빠른 시작

### 1. 마켓플레이스 등록 (처음 한 번만)

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. 플러그인 설치

```
/plugin install insane-research
```

### 3. Claude Code 재시작

캐시는 시작 시 로드됩니다 — 설치 후 반드시 재시작하세요.

### 4. 리서치 시작

```
/insane-research AI 코드 어시스턴트의 생산성 영향
```

Claude가 몇 가지 스코핑 질문을 한 뒤, 병렬 리서치 에이전트를 배포하고 구조화된 리포트를 전달합니다.

---

## 왜 insane-research인가?

- **순차 검색이 아닌 병렬 에이전트** — 3-5개의 에이전트가 웹, 학술, 기술 문서를 동시에 검색하여 리서치 시간을 대폭 단축
- **소스 품질 등급 (A–E)** — 모든 소스에 피어리뷰 논문(A)부터 추측성 포스트(E)까지 등급을 부여해 신뢰도를 명확히 표시
- **할루시네이션 방지** — 모든 사실적 주장에 인라인 인용 필수, 핵심 주장은 최소 2개 독립 소스로 교차 검증
- **세션 이어하기** — 리서치 상태가 `state.json`에 저장되어 중단 후 언제든 재개 가능
- **완전한 산출물** — 경영진 요약, 섹션별 전체 리포트, 참고문헌, 선택적 인터랙티브 웹사이트까지 자동 생성

---

## 동작 방식

```
사용자 질문
    │
    ▼
Phase 1: 질문 정제 (Scoping)
  └─ AskUserQuestion → 관심 분야, 깊이, 대상 독자, 소스 유형
    │
    ▼
Phase 2: 검색 계획 (Retrieval Planning)
  └─ 3-5개 하위 토픽 분해 → 검색 쿼리 생성 → 계획 승인
    │
    ▼
Phase 3: 반복 쿼리 (Iterative Querying)  ←────────────────┐
  ├─ 웹 리서치 에이전트 (x2-3)                            │
  ├─ 학술/기술 에이전트 (x1-2)                            │ 부족 시 재시도
  └─ 교차검증 에이전트 (x1)                               │
    │                                                      │
    ▼                                                      │
Phase 4: 소스 삼각검증 (Source Triangulation) ────────────┘
  └─ 핵심 주장 교차 확인 (≥2 소스) → A–E 품질 등급 부여
    │
    ▼
Phase 5: 지식 합성 (Knowledge Synthesis)
  └─ 구조화 → 섹션 작성 → 인라인 인용 삽입
    │
    ▼
Phase 6: 품질 보증 (Quality Assurance)
  └─ 할루시네이션 체크 → 인용 검증 → 완성도 점검
    │
    ▼
Phase 7: 산출물 패키징 (Output & Packaging)
  └─ 경영진 요약 + 전체 리포트 + 참고문헌 + 웹사이트 (선택)
```

---

## 커맨드

| 커맨드 | 설명 |
|--------|------|
| `/insane-research [주제]` | 새로운 리서치 세션 시작 |
| `/insane-research resume [session_id]` | 이전 세션 이어하기 |
| `/insane-research status` | 모든 세션 진행 상황 확인 |
| `/insane-research query` | 구조화된 쿼리 빌더 실행 |
| `/insane-research` | 인터랙티브 메뉴 열기 |

### 자연어 트리거

```
딥리서치 [주제]
[주제]에 대해 리서치해줘
[주제] 리서치
심층 연구 [주제]
deep research on [topic]
```

---

## 에이전트

Phase 3에서 세 가지 유형의 에이전트가 병렬로 실행됩니다:

| 에이전트 | 수량 | 역할 |
|---------|------|------|
| 웹 리서치 | 2–3 | 최신 뉴스, 트렌드, 시장 데이터 |
| 학술/기술 | 1–2 | 논문, 스펙, 공식 문서 |
| 교차검증 | 1 | 핵심 주장 팩트체크 |

---

## 소스 품질 등급

| 등급 | 유형 | 예시 |
|------|------|------|
| **A** | 피어리뷰, 체계적 리뷰 | Nature, Lancet, IEEE |
| **B** | 공식 문서, 임상 가이드라인 | FDA, W3C, WHO |
| **C** | 전문가 의견, 산업 리포트 | Gartner, 컨퍼런스 |
| **D** | 프리프린트, 화이트페이퍼 | arXiv, 기업 블로그 |
| **E** | 일화적, 투기적 | 소셜미디어, 포럼 |

---

## 산출물 구조

```
RESEARCH/{topic}_{timestamp}/
├── state.json                    # 세션 상태 (이어하기용)
├── README.md                     # 네비게이션 가이드
├── outputs/
│   ├── 00_executive_summary.md   # 3–5페이지 경영진 요약
│   ├── 01_full_report/           # 섹션별 전체 리포트
│   ├── 02_appendices/            # 부록
│   └── comparison_data.json      # 구조화된 비교 데이터
├── sources/
│   ├── sources.jsonl             # 수집된 소스
│   ├── bibliography.md           # 참고문헌
│   └── quality_report.md         # 소스 품질 평가
└── website/                      # (선택) 인터랙티브 웹 프레젠테이션
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## 요구사항

- [Claude Code](https://docs.anthropic.com/claude-code) CLI
- WebSearch (빌트인) 또는 웹 검색 MCP 서버

### 권장 MCP 서버 (검색 커버리지 향상, 선택)

- Firecrawl
- Google Search MCP
- Exa Search

---

## 라이선스

MIT

---

<div align="center">

**출처를 인용하는 리서치. 항상.**

</div>
