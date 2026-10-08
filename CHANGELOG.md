# Changelog

## [2.10.0] - 2026-10-08

### Added — 원문 인용 게이트 (고위험 주장은 원문 구절 대조 필수)

- **배경**: 과거 리서치에서 verified로 통과한 고위험 주장 8건 중 4건은 수치·경로·속성이 인용 출처에 없었다(IP-Adapter CLIP-I 0.828, Stability `v2alpha`→`v2beta` 오기 등). 게이트는 출처 개수·등급·유형만 보고 주장이 출처에 실제로 있는지는 보지 않았다.
- 주장 레코드에 `evidence[]`({source_id, quote, locator?}) 추가. 팬아웃 에이전트는 `source_url`로 쓰고 `merge_agent_returns.py`가 `src_xxx`로 바꾼다.
- **`scripts/snapshot_sources.py` 신규** — high-risk 주장이 인용한 출처만 insane-search 엔진으로 받아 `sources/snapshots/`에 저장, sources.jsonl에 `snapshot`(path·sha256·status) 기록. WebFetch는 모델 요약이라 쓰지 않는다.
- **`validate_ledger.py` 7a~7e**: high-risk인데 evidence 없음·구절이 원문에 없음·스냅샷 없음·sha256 불일치·길이(20~300자) 위반이면 unresolved. evidence의 source_id가 주장의 source_ids 밖이면 하드 에러. 대조는 NFKC·따옴표·마크다운 기호·공백·대소문자만 정규화한 부분 문자열 일치(퍼지 금지).
- `state.json`의 `ledger_schema: 2` 세션에만 적용(기존 세션은 이전 규칙). `orchestrator.py`의 새 세션은 2로 시작.
- 검증: `tests/test_evidence_gate.py` 12건(지난 표본 8건 재현 4 verified/4 unresolved, 날조·차단·변조·구스키마 면제), `tests/test_snapshot_sources.py` 4건, 실제 리서치 에이전트 2개 E2E(실엔진 스냅샷 10/10, high-risk 7건 구절 대조 통과, 구절 변조 시 unresolved).

## [2.9.0] - 2026-08-19

### Fixed — 데이터 흐름 락 실효화 (게이트 실패가 실제로 합성을 막게)

- **`validate_ledger.py`가 exit≠0에서도 `verified_claims.json`을 써서 락이 헐거웠던 문제 수정.** 실패 시 allowlist를 생성하지 않고 **이전 실행이 남긴 파일도 삭제**한 뒤 `outputs/gate_failed.json`(exit_code·kind·reasons·next_step)을 남긴다 — 실패 상태에서는 합성 입력이 물리적으로 존재하지 않는다. 통과 시 마커는 자동 제거. 실측 배경: `RESEARCH/akamai-bypass_20260723_120129`는 절차위반 40건(exit 1, `passed=false`)인데도 전체 보고서가 생성돼 있었다.
- 하드 에러(exit 2)에서도 `state.json.verification`에 `passed=false`·`blocked` 사유를 남긴다(이전에는 아무 기록도 남기지 않아 "게이트 미실행"과 구분 불가).

### Added — 보고서 본문 대조 게이트 `scripts/verify_report.py`

- 보고서가 **verified 주장만 단정형으로 인용했는지** 코드로 대조한다. 게이트 통과 후 본문에 미검증 문장을 쓰는 경로가 무방비였던 공백을 메움.
- 검사: ①`gate_failed.json`/`verified_claims.json` 부재 → exit 2 ②unresolved·refuted claim_id를 annex 밖 본문에 인용 → exit 1 ③ledger에 없는 유령 claim_id 인용 → exit 1 ④verified 인용 0건 → exit 1, 커버리지 미달(`--min-coverage`) → exit 1.
- annex 구역은 마크다운 제목(미확정/Unresolved/반증/Refuted/부록/Annex/Appendix)으로 판정하며, 같거나 상위 레벨의 새 제목에서 구역이 끝난다. 결과는 `state.json.report_verification`에 기록.

### Added — 미확정 비율 계측

- `unresolved_ratio`를 계산해 `state.json.verification`에 기록하고, 임계치(기본 0.5, `--max-unresolved-ratio`) 초과 시 `[WARN]` 출력. exit code는 바꾸지 않는다 — 통과 여부만 보면 "84건 중 42건 미확정인데 passed=true"(fastapi-fastmcp 세션 실측) 같은 얕은 근거를 놓치기 때문.

### Changed — 자기신고 필드의 증적 승격 (2026-08-24, breaking)

- **`counter_search` 구조체 강제**: high-risk 주장의 counter_search는 `{query, urls, summary}` 구조체여야 한다. 자유 문자열은 감사 불가 → 절차 위반(exit 1). `urls`의 각 URL은 sources.jsonl에 등록돼 있어야 하며 미등록 시 하드 에러(exit 2). 반증 검색을 "했다고 쓰는 것"이 아니라 실행 쿼리·열어본 소스로 감사 가능하게.
- **`primary_source` 파생 계산**: 주장 레코드의 자기신고를 무시하고 소스 `type`(`PRIMARY_SOURCE_TYPES`: standards_document/official_docs/government/filing/peer_reviewed/repository/api 등)에서 계산한다. 출력 레코드의 primary_source도 파생값으로 덮어쓴다.
- **독립성 단위 도메인 → 조직(org)**: peps.python.org + docs.python.org가 독립 2개로 세어지던 구멍 봉합(2.9.0 라이브 테스트에서 실측 발견). 소스 `org` 필드로 명시 지정 가능, 없으면 eTLD+1 근사 추론(github.io류 호스팅 도메인·co.kr류 2단 접미사는 예외 목록으로 3레이블 유지).
- **high-risk 다중 표면 강제**: 소스 표면(type) 2종 미만이면 unresolved — SKILL.md가 프롬프트로만 권고하던 "다중 표면 대조"를 코드 게이트로. 
- 스키마 문서 정렬: SKILL.md·phase_contracts.md·workflow_fanout.md(AGENT_RETURN_SCHEMA counter_search object화)·merge 테스트 픽스처.

### Tests

- `tests/test_validate_ledger.py` +5(락 하드닝·스테일 삭제·마커 정리·비율 경고) +9(counter 구조체·URL 대조·조직 독립성·호스팅 예외·org 오버라이드·파생 primary·표면 다양성·normal 면제), `tests/test_verify_report.py` 신규 9종. suite 22 → 45 passed.

## [2.8.2] - 2026-07-23

### Fixed — strict 핸드오프 스키마 정렬

- `pipelines.py`의 `strict_verification_handoff()`가 v2.5.0+ 장부 스키마에 없는 키(claim/verification_question 및 파생 필드)를 읽어 항상 빈 페이로드를 내던 드리프트 수정 — 실제 스키마(claim_id/text/source_ids + status/status_reason)로 정렬, status 부재 레코드는 "모르면 미확정" 원칙대로 unresolved 취급.
- 스테일 중복 분류기 `classify_claim_status()` 삭제 — 분류 SSOT는 `validate_ledger.classify_claim`(counter-search·execution_proof·충돌 검사 포함).
- 회귀 테스트 `tests/test_strict_handoff.py` 2종 추가 (suite 22 passed).

## [2.8.1] - 2026-07-23

### Changed — 엔진 위임 비동기 기본화

- insane-search 위임을 **background-first 패턴**으로 전환: 백그라운드 시작 → ~15초 빠른 수거(대부분 경로는 여기서 인라인과 동일) → 미완료 시 다음 조사 병행 → **반환 전 전량 수거 게이트(불가침)**, URL당 90초 초과 시 실패 기록 후 대체 소스 전환. 어려운 WAF 격자(최악 ~65초, 벤치에서 17회 시도 실측)가 에이전트 전체를 세워두는 문제 해소. 같은 도메인에서 긴 격자를 겪은 뒤에는 폴링 없이 바로 병행. `access` 메타에 `async` 표시.
- 조건 판정형(R7식 발동 조건) 대신 기본 패턴으로 설계한 이유: 에이전트가 실행 중 verdict를 관찰할 수 없어 조건형은 실전에서 발동되지 않기 때문.

## [2.8.0] - 2026-07-23

### Added — Workflow 팬아웃 모드 (공식 문서 + 실측 프로브 근거)

- **Phase 3 실행 모드 선택**: 세션에 Workflow 도구가 있으면 **팬아웃 모드**(폭 5-6, `references/workflow_fanout.md`), 없으면 기존 배치 모드(2-3, Rate-Limit Guard) 폴백. 실측: 6폭 버스트 6/6 무사고(3.8s), 리서치형 5폭 5/5 무사고(16s).
- **AGENT_RETURN_SCHEMA 강제 반환 + 결정론 취합기** `scripts/merge_agent_returns.py`: 에이전트 JSON 반환 배열 → sources.jsonl(URL dedup·전역 id)/claim_ledger.jsonl(URL→id 매핑)/expansion_log.md/query_log.md(교차 에이전트 쿼리 중복 표시) 자동 생성 — 벤치 실측 병목(수작업 병합 ~7분) 제거. 취합 산출물이 validate_ledger 게이트에 무수정으로 물리는 것까지 테스트(총 19 pytest).
- **검색 예산 회계**: Claude Code 세션당 WebSearch 200회 캡(전 서브에이전트 합산, 초과 시 조용한 no-op — v2.1.212+) 대응. 축당 예산 배분, search_count 합산·80% 경고, "빈 검색 연속 = 캡 의심" 진단 규칙.
- **WebFetch 손실성 명시**: "부재 판정은 WebFetch로 하지 않는다" (공식 lossy-by-design 근거).

## [2.7.0] - 2026-07-22

### Added — ULW 흡수 (insane 강점 유지 + ulw-research 메커니즘 채용)

근거: `RESEARCH/lazycodex_ulw_vs_insane_20260722_140015/outputs/` 비교 분석 2편.

- **접근 3단 에스컬레이션 (P1-0)**: Phase 3 접근을 WebFetch → **insane-search 엔진 위임**(설치 시, `python3 -m engine --json --trace` 계약 + `⛔ NOT EXHAUSTED`/untried_routes 준수 + R8 untrusted 취급) → 내장 폴백 체인으로 명문화. tool_strategy.md에 엔진 탐지·호출 계약 섹션 신설, 접근 SSOT를 insane-search 플러그인으로 선언(드리프트 방지). sources.jsonl에 `access` 메타(layer/verdict/profile_used/extraction_source/phase) 추가.
- **EXPAND 리드 확장 루프 (P1-1)**: 모든 리서치 에이전트 응답 꼬리에 `## EXPAND`(LEAD/WHY/ANGLE | DEAD END | none) 필수. `artifacts/expansion_log.md` 전수 dedup(기각 리드 포함) + 명시적 수렴 규칙(미확인 리드 0 / 2연속 무신규 배치 / 깊이 4 도달 시 사용자 질의). 확장 배치는 기존 Rate-Limit Guard(2-3 동시) 내에서만.
- **executable 실행 검증 (P1-2)**: `claim_type: "executable"` + `execution_proof`(script/output/env/verdict) 스키마 추가. `validate_ledger.py`가 executable 주장에 실행 증적을 강제 — 누락 시 exit 1, confirmed는 독립 교차검증 대체, refuted/partial은 annex행. `tests/test_validate_ledger.py` 신규(10 케이스: 기존 회귀 5 + executable 5).
- **스폰 메시지 표준 3요소 (P1-3)**: agent_prompts.md에 예산 해제문·완료 정의·EXPAND 꼬리 필수화 — 서브에이전트의 "찾으면 정지" 브레이크를 명시적으로 풀지 않으면 얕은 답이 돌아오는 문제 대응.
- **검색 크래프트 (P1-4)**: tool_strategy.md에 연산자 변주 표(site:/filetype:/intitle:/inurl:/exact/-term/OR/before:/after:), 에이전트당 최소 8-10 상이 쿼리, 고수익 조합, 언어 정책(주제 1차 언어 우선 스윕).
- **시간 유효성 분리 (P2)**: sources·ledger에 `observed_at`(수집 시각)/`valid_at`(내용 유효 시점) 필드 — 릴리즈 노트/과거 기사/현재 상태 주장 혼동 방지.
- **리포트 시각화 기본화 (P2)**: full_report_section.md에 Mermaid 다이어그램 슬롯("정량은 차트, 구조·인과는 Mermaid"), website_template.html에 mermaid@11.16.0(SRI 핀) + 다이어그램 블록.

### Added — 실전 벤치마크(2026-07-22, vs ulw-research) 후속 보강
- **eval_report.py annex 예외**: Unresolved/Refuted annex 섹션은 leak 스캔에서 제외(헤딩 기반 섹션 스트립) — 계약이 요구하는 annex 나열이 leak으로 오탐되던 모순 해소. `tests/test_eval_report.py` 신규(5 케이스: annex 인용 무해·한국어 헤딩·본문 누출 FAIL 유지·annex 경계·dangling 회귀).
- **다중 표면 삼각측량**: 도메인 독립 ≠ 내용 대조 — 조직 구성/버전/법률 주장은 이질 표면(공식 페이지 vs 저장소 파일 vs 기계판독 API) 대조를 요구(SKILL.md Phase 4 + tool_strategy.md). 벤치에서 도메인 2개 통과 주장의 표면 충돌(TSC 소속)이 실측된 데서 도출.
- **표준 분모 소스**: 채택률·점유율 주장은 벤더 설문 대신 중립 분모(SO Developer Survey·DB-Engines·repology) 우선 — 크래프트 고수익 조합에 추가.

### Fixed
- tool_strategy.md 스테일 접근 경로 정정: Reddit 비인증 `.json`+모바일 UA 안내 폐기(WAF 403 실측) → `.rss`+curl_cffi로 교체, Google 캐시(2024-07 종료) 제거 → Wayback/archive.today로 대체.

### Infra (마켓플레이스 레포)
- `tools/validate_skill_contracts.py` — 불가침 계약 문구 18종 grep-assert CI 게이트, validate-commands 워크플로우에 연결.

## [2.6.0] - 2026-06-22

### Added
- **`scripts/eval_report.py` — 결정론적 평가 채점기**(측정 도구, LLM judge 없음). 리서치 세션 산출물을 받아 검증 게이트의 실제 효과를 4지표로 계측:
  - `leak_rate`(unresolved/refuted 주장이 본문에 샜는가 — verified-only 게이트 효과의 직접 지표), `citation_resolution_rate`(깨진 인용), `orphan_source_rate`(미인용 소스), `verified_coverage_rate`(allowlist가 실제 소비됐는가).
  - leak/coverage 판별은 content char 6-gram + verified 맥락 제외로 버전번호 등 공유 토큰 오탐 방지. verdict FAIL(leak 또는 dangling citation 존재) 시 exit 1.
  - good/bad 픽스처로 판별력 검증(GOOD=PASS leak0, BAD=FAIL leak2+dangling+orphan).
- SKILL.md Phase 7에 마감 자기검증(`eval_report.py`) 단계 추가, Scripts 표에 authoritative 등록.

### Why
"개선이 진짜 효과 있나"를 측정할 수단이 없었음(GPT 리뷰도 평가 harness 부재 지적). 이제 검증 게이트 효과를 숫자로 확인하고, 이후 개선마다 게이트 on/off A/B·회귀 추적 가능.

## 2.5.1 — 2026-06-21

- The GitHub-star prompt is shown in the user's current language; on a fresh session with no language signal yet, it falls back to the language detected from your recent Claude sessions (else English).
- GitHub star is now **opt-in** — on first run the command asks once via AskUserQuestion (`네, ⭐ 눌러주기` / `아니요`) instead of auto-starring. The star logic moved into `setup.sh` and records the choice (`~/.gptaku-setup/<plugin>.star.json`) so it never re-asks. `setup.sh` no longer stars anything automatically.

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
