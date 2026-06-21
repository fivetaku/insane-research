# Changelog

## [2.5.0] - 2026-06-21

### Added
- **`scripts/validate_ledger.py` — 결정론적 검증 게이트** (control plane이 아닌 단일 체커).
  - claim ledger(`artifacts/claim_ledger.jsonl`) + `sources.jsonl`을 읽어 주장 status를 **코드로 계산**(독립 도메인 ≥2, counter_search 존재, 1차소스, B등급 이상).
  - `outputs/verified_claims.json` 생산 + `state.json`에 sha256 `verification.signature` 기록.
  - 종료코드: 0=통과 / 1=프로세스 위반(high-risk counter_search 누락) / 2=하드 에러(스키마·미등록 source id·**A-E 등급 모순**).

### Changed
- **SKILL.md 검증을 "권고"에서 "코드 게이트"로 전환** (agent-council B 노선 + GPT-5.5 Pro 리뷰 반영):
  - Phase 4: claim ledger를 `artifacts/claim_ledger.jsonl`(JSONL)로 명문화, `status`는 체커가 계산(직접 작성 금지).
  - Phase 5: **verified-only 합성 게이트** — 핵심 주장은 `outputs/verified_claims.json`만 근거(데이터 흐름 락).
  - Phase 6: `validate_ledger.py` 실행을 명령과 함께 **하드 게이트**로 규정(exit≠0 시 Phase 7 진입 금지).
  - A-E 등급표를 `quality_rubric.md` SSOT에 정렬(Gartner/McKinsey research=B 등 파일 간 모순 해소).
  - 스코핑 우선순위를 단일 규칙으로 통합("무조건 즉시 질문" 충돌 제거).
  - Scripts 표에서 `orchestrator.py`/`pipelines.py`를 helper(정적 자산)로 강등, `validate_ledger.py`를 authoritative로.
- `tool_strategy.md` 병렬 에이전트 예시를 기본 **foreground 배치**로 수정(경고와 모순되던 `run_in_background=True` 복붙 예시 제거).

### Why
GPT-5.5 Pro 코드리뷰: SKILL.md 검증 계약과 Python 코드가 미연결 → 검증이 LLM 자율에 의존(권고). classify_claim_status가 counter_search 존재조차 검사 안 함, 합성이 raw findings를 그대로 수용. agent-council(agy/Claude) 합의 = "오케스트레이션은 프롬프트, 검증은 코드"로 분리하고 단일 결정론 체커를 스킬이 반드시 호출하게.

## [2.2.2] - 2026-05-04

### Changed
- SKILL.md "Research Type별 권장 골격" → **"Research Type 기반 골격 동적 생성"**
  - 5 type 표를 "메뉴"가 아닌 "패턴 학습용 예시"로 명시
  - 적용 절차에 "**사용자 주제에 맞춰 5 섹션 명을 동적 생성**" 단계 추가
  - 섹션 명을 그대로 카피하지 말고 사용자 주제에 맞춰 변환하라 명시
  - "새 type 사례를 본 표에 추가하지 말 것" 가드 추가

### Why
v2.2.1의 type별 매핑 표가 약한 fossil 위험 (섹션 명 하드코딩).
사용자 지적: 카탈로그를 메뉴로 쓰면 새 fossil이 됨 → 예시 + 동적 생성으로 명시.

## [2.2.1] - 2026-05-04

### Added
- SKILL.md "Research Type별 권장 골격" 섹션 — Exploratory/Comparative/Predictive/Analytical/Generic 5 type 매핑 (advanced opt-in)

### Preserved (모든 결정 contract 그대로 유지)
- 7-Phase 강제 + 기본 5섹션 보고서 골격 (resume protocol)
- A-E source quality 등급 + minimum 2 sources
- citation 5 elements (Author/Date/Title/URL/Page)
- Hallucination Prevention 4 strategies
- state.json / sources.jsonl schema
- Date-aware query generation (CRITICAL)

→ ADDITIVE only. 기본 동작은 그대로, type별 골격은 사용자 명시 confirm 시에만 사용.

## [2.2.0] - 2026-03-16

### Added
- Tier 2.5 fallback strategy — 차단된 사이트에 대한 대체 접근 전략 추가

## [2.1.0] - 2026-03-10

### Fixed
- allowed-tools에서 AskUserQuestion 제거 — auto-approve로 UI가 렌더링되지 않던 버그 해결
- SKILL.md에 EXECUTE 키워드 + markdown preview 적용

### Changed
- .gitattributes 추가 — CRLF/LF 정규화

## [2.0.0] - 2026-02-28

### Changed
- 멀티에이전트 소스 검증 파이프라인 도입 (7단계)
- 구조화된 리포트 생성 기능 강화
- plugin.json 메타데이터 보강 (homepage, repository, license 추가)

## [1.1.0] - 2026-02-25

### Changed
- CCPS v2.0 플러그인 표준으로 전체 구조 리팩토링

## [1.0.1] - 2026-02-24

### Fixed
- README 영문 통일, 로컬 저장 이점 설명 보강

## [1.0.0] - 2026-02-23

### Added
- 최초 릴리스
- AI 기반 딥 리서치 스킬
- 로컬 저장소에 리서치 결과 자동 저장
