# Changelog

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
