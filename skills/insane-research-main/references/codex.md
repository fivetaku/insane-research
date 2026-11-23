# Codex에서 실행할 때 (insane-research)

SKILL.md 절차는 그대로 따르고, 아래 차이만 적용한다. query·refs 스킬도 이 문서를 같이 쓴다.

## 질문 = 질문 도구 (이번 세션 도구 목록으로 판단)

1. `request_user_input_async`가 있으면 AskUserQuestion 1콜 = 이 도구 1콜(문항 ≤4).
   - 형식: `{"questions":[{"title":"헤더 — 한 줄 질문","options":["추천안 (추천) — 설명","대안 — 설명"]}]}`
   - 문항에는 `title`·`options`만. `question`·`header`·`id`를 넣으면 파싱 오류가 난다. 추천안을 맨 앞에, "기타" 옵션은 넣지 않는다.
   - 부른 뒤 "위 질문에 답해 주시면 이어서 진행합니다" 한 줄만 쓰고 턴을 끝낸다. 답은 다음 사용자 메시지로 온다.
2. Plan 모드라 `request_user_input`만 있으면: 1콜 3문항까지(넘으면 나눈다). `header`(12자 이내)·`id`(snake_case)·`question`, 선택지 `label`·`description`, 추천 라벨 끝에 `(Recommended)`.
3. 둘 다 없으면 채팅에 번호 블록(`Q1. …` / `1. 추천안 — …` / `2. 대안 — …` / `3. 문장으로 직접 적기`)을 내고 답을 기다린다. "모르면 1번으로 진행"을 덧붙인다.
4. `codex exec`처럼 사람이 답할 수 없는 실행이면 묻지 않고 기본값(종합 리포트·전체 소스)으로 진행하고 `state.json`에 가정을 기록한다.

`markdown`(프리뷰) 필드는 보여 줄 곳이 없다. 메뉴·옵션 설명은 도구를 부르기 직전 채팅에 짧은 목록으로 먼저 쓴다. `multiSelect`는 제목 끝에 "(여러 개면 쉼표로)"를 붙인다. 열린 질문(주제 묻기)은 도구 없이 평범한 채팅 질문으로 한다.

## Codex에 없는 도구

- **Agent/Task 팬아웃(Phase 3)**: `spawn_agent(agent_type="explorer", prompt=…)`로 축마다 서브에이전트를 스폰한다. 반환은 `references/workflow_fanout.md`의 JSON 스키마 하나로 요구하고 `merge_agent_returns.py`로 취합한다. 스폰이 불가·제한이면 메인 스레드에서 축을 순차 실행한다(`state.json` `exec_mode`에 `sequential` 기록). Workflow 도구는 없으므로 팬아웃 모드의 Workflow 전용 단계는 `spawn_agent` 또는 순차로 대신한다. 폭은 SKILL.md의 8~10을 상한으로 하되 호스트 호출 한도에 걸리면 줄인다.
- **strict 핸드오프의 `Workflow({name:"deep-research"})`**: 없다. 해당 high-risk 주장은 `spawn_agent` 3개의 독립 반박 시도 후 다수결로 대신하거나, 불가하면 `unresolved`로 남긴다.
- **다른 스킬(`Skill`) 호출**: 그 스킬의 SKILL.md를 열어 절차를 따른다. 인자 `query`/`refs`는 `../insane-research-query/SKILL.md`·`../insane-research-refs/SKILL.md`를 연다.
- **insane-search 엔진**: 스크립트가 기본으로 찾는 `~/.claude/plugins/cache/...`가 Codex에 없으면 엔진 폴더(`…/insane-search/skills/insane-search`, Codex 캐시는 `~/.codex/plugins/cache/*/insane-search*/*/skills/insane-search`)를 찾아 `snapshot_sources.py`·`collect_ref_images.py`에 `--engine-dir`로 넘기거나 `INSANE_SEARCH_ENGINE_DIR`로 지정한다. 엔진이 없으면 `tool_strategy.md`의 폴백 체인을 쓰고 `access_layer`를 `builtin-fallback`으로 기록한다.

## 그 밖의 차이

- 첫 실행 설정(`setup/setup.sh`)은 Claude Code 전용이다. Codex에서는 실행하지 않는다.
- 스킬 안의 `${CLAUDE_PLUGIN_ROOT}`는 치환되지 않는다 — 플러그인 루트로 직접 바꿔 읽는다.
