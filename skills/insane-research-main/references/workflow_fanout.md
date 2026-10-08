# Workflow 팬아웃 모드 (Phase 3 실행부 — v2.8)

Phase 3의 검색 실행을 Claude Code 네이티브 **Workflow 도구**로 수행하는 모드. 실측 근거(2026-07-23): 6폭 버스트 6/6 무사고(3.8s), 리서치형(웹검색 수행) 5폭 5/5 무사고(16s). 공식 문서상 동시 16캡·런당 1,000 에이전트이며, 구독 플랜에 "동시 에이전트 수" 제한은 문서화돼 있지 않다(사용량 윈도우만 존재).

## 모드 선택 (Phase 3 진입 시 1회)

| 조건 | 모드 |
|---|---|
| 세션 도구 목록에 Workflow가 있음 | **팬아웃 모드** (이 문서) — 폭 5-6 |
| Workflow 없음 (Pro 미활성·구버전·비활성화) | **배치 모드** — 기존 Rate-Limit Guard(2-3 동시, SKILL.md) |

판정을 `state.json`에 기록: `"exec_mode": "workflow-fanout" | "agent-batch"`.

## 에이전트 반환 스키마 (AGENT_RETURN_SCHEMA)

모든 리서치 에이전트는 이 스키마로 **강제 반환**된다(`agent(prompt, {schema})` — 프롬프트 준수가 아니라 도구 계층 검증). 이 JSON이 곧 취합 입력이므로 수작업 병합이 사라진다.

```json
{
  "type": "object",
  "required": ["axis", "sources", "claims", "expand_leads", "queries_run", "search_count"],
  "properties": {
    "axis": {"type": "string"},
    "findings_summary": {"type": "string"},
    "sources": {"type": "array", "items": {"type": "object",
      "required": ["url", "title", "domain", "quality_rating"],
      "properties": {"url": {"type": "string"}, "title": {"type": "string"}, "domain": {"type": "string"},
        "date": {"type": "string"}, "valid_at": {"type": "string"}, "type": {"type": "string"},
        "quality_rating": {"type": "string", "enum": ["A", "B", "C", "D", "E"]},
        "access": {"type": "object"}}}},
    "claims": {"type": "array", "items": {"type": "object",
      "required": ["text", "risk", "claim_type", "source_urls"],
      "properties": {"text": {"type": "string"}, "risk": {"type": "string", "enum": ["high", "normal"]},
        "claim_type": {"type": "string", "enum": ["numeric", "legal", "causal", "descriptive", "executable"]},
        "source_urls": {"type": "array", "items": {"type": "string"}},
        "counter_search": {"type": "object", "properties": {"query": {"type": "string"}, "urls": {"type": "array", "items": {"type": "string"}}, "summary": {"type": "string"}}, "required": ["query"]},
        "conflicting": {"type": "boolean"}, "valid_at": {"type": "string"},
        "execution_proof": {"type": "object"},
        "evidence": {"type": "array", "items": {"type": "object",
          "required": ["source_url", "quote"],
          "properties": {"source_url": {"type": "string"}, "quote": {"type": "string", "minLength": 20, "maxLength": 300},
            "locator": {"type": "string"}}}}}}},
    "expand_leads": {"type": "array", "items": {"type": "object",
      "required": ["lead", "why", "angle"],
      "properties": {"lead": {"type": "string"}, "why": {"type": "string"}, "angle": {"type": "string"}}}},
    "queries_run": {"type": "array", "items": {"type": "string"}},
    "access_log": {"type": "array", "items": {"type": "object"}},
    "search_count": {"type": "integer"}
  }
}
```

**`evidence` 작성 규칙 (v2.10.0 — `risk: "high"` 주장은 필수)**: 주장을 뒷받침하는 **출처 원문 구절을 그대로** 복사한다(20~300자). 요약·의역·번역 금지 — 한국어 주장이어도 영어 출처면 영어 원문 그대로. `source_url`은 같은 반환의 `sources[].url` 중 하나여야 한다(취합기가 `src_xxx`로 바꾼다). 수치·경로·버전·고유명사가 주장에 있으면 그 값이 들어 있는 구절을 고른다. 게이트는 이 구절이 저장된 원문 스냅샷에 실제로 있는지 문자열로 대조하므로, 원문에 없는 문장은 그 주장을 unresolved로 떨어뜨린다. `locator`(소제목·표 이름 등)는 선택.

## 스크립트 템플릿 (주제·축에 맞춰 즉석 변형)

에이전트 프롬프트에는 기존 계약 전부를 포함한다: 예산 해제문·완료 정의·검색 크래프트(8-10 쿼리)·insane-search 위임(**비동기 기본 — 백그라운드 시작·빠른 수거·반환 전 전량 수거**, tool_strategy.md §비동기 위임)·R8·**검색 예산**(아래). `{...}` 슬롯을 채워 사용.

```javascript
export const meta = {
  name: 'research-fanout',
  description: '{TOPIC} — 축별 리서치 팬아웃 + 확장 1라운드',
  phases: [{ title: 'Fanout' }, { title: 'Expand' }],
}
const SCHEMA = /* 위 AGENT_RETURN_SCHEMA 붙여넣기 */
const AXES = [/* {key, prompt} — Phase 2에서 정한 3-6개 축. 축별 프롬프트에 검색 예산 N회 명시 */]

phase('Fanout')
const wave1 = (await parallel(AXES.map(a => () =>
  agent(a.prompt, { label: `axis:${a.key}`, phase: 'Fanout', schema: SCHEMA })
))).filter(Boolean)

// 리드 dedup 후 확장 1라운드 (깊이 추가는 오케스트레이터가 재호출로)
const seen = new Set()
const leads = wave1.flatMap(r => r.expand_leads.map(l => ({ ...l, from: r.axis })))
  .filter(l => { const k = l.lead.toLowerCase().slice(0, 60); if (seen.has(k)) return false; seen.add(k); return true })
  .slice(0, 6)  // 확장 폭 상한 — 검색 예산과 함께 과확장 방지

phase('Expand')
const wave2 = (await parallel(leads.map(l => () =>
  agent(`확장 조사: ${l.lead}\n이유: ${l.why}\n제안 각도: ${l.angle}\n출처 축: ${l.from}\n` +
        `{공통 계약 블록 — 예산 해제·크래프트·위임·R8·검색 예산 4회}`,
    { label: `lead:${l.lead.slice(0, 20)}`, phase: 'Expand', schema: SCHEMA })
))).filter(Boolean)

return { returns: [...wave1, ...wave2], leads_total: leads.length }
```

오케스트레이터 후처리 (Workflow 완료 알림 수신 후):

```bash
# 1) 반환 배열을 세션에 저장 (Workflow result의 returns 필드)
#    → <session>/artifacts/agent_returns.json
# 2) 결정론 취합 — sources.jsonl / claim_ledger.jsonl / expansion_log.md / query_log.md 생성
python3 "${CLAUDE_PLUGIN_ROOT}/skills/insane-research-main/scripts/merge_agent_returns.py" --session "<session>"
# 3) 이후는 기존 파이프라인 그대로: 부족 주장 보강 → validate_ledger.py → 합성 → verify_report.py → eval_report.py
```

## 검색 예산 회계 (⚠️ 필수 — 세션 200캡 대응)

Claude Code는 **세션당 WebSearch 200회**(메인+모든 서브에이전트 합산)를 캡하며, 초과분은 에러가 아니라 **조용한 빈 검색**이 된다(v2.1.212+). 규칙:

1. Phase 2에서 축당 검색 예산을 배분해 각 에이전트 프롬프트에 명시한다 (권장: 1라운드 축당 10회, 확장 에이전트 4회 — 축 5개+확장 6개 ≈ 74회).
2. 에이전트는 `search_count`를 반환하고, merge_agent_returns.py가 합산해 80% 초과 시 경고한다.
3. 진단 규칙: **검색이 갑자기 계속 빈 결과만 주면 캡 도달을 의심**한다 (에러가 아니므로 재시도 금지 — 이미 수집한 정보로 진행하거나 사용자에게 `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION` 상향 안내).
4. 같은 세션에서 리서치를 연속 실행하면 캡이 누적된다 — 대형 리서치는 새 세션 권장.

## 폭·안전 규칙

- 1라운드 폭 5-6, 확장 라운드 폭 ≤6. **한 번에 10 이상 제출 금지**(실측 검증 범위 밖 + 대형 워크플로 경고 임계).
- Workflow 에이전트는 항상 acceptEdits + allowlist 상속 — 장시간 실행 전 allowlist 확인(권한 프롬프트가 실행을 멈출 수 있음).
- 실패 에이전트는 null로 돌아온다 — `.filter(Boolean)` 후 **누락 축을 반드시 보고**하고, 빠진 축은 배치 모드로 보충한다(조용한 커버리지 구멍 금지).
- 세션 종료 시 워크플로는 재개 불가(세션 스코프) — 완료 에이전트 캐시는 같은 세션 내 resume에서만 유효.
