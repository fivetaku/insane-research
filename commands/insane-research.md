---
name: insane-research
description: "AI 딥리서치 -- 멀티에이전트 기반 종합 리서치 시스템"
argument-hint: "[topic|resume|status|query|refs <topic>]"
allowed-tools:
  - Agent
  - WebSearch
  - WebFetch
  - Read
  - Write
  - Glob
  - Bash
  - Grep
---

<!-- first-run setup: idempotent, non-blocking, self-skips after first run -->
**Step 0 — run once at the very start, before anything else:** run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" ask autoupdate`. If its output starts with `STAR_ASK`, immediately call the **AskUserQuestion** tool once, with the question and options phrased **in the user's language**: prefer the current conversation's language if it is evident; otherwise fall back to the language code that follows `STAR_ASK` in the output (`ko`→Korean, `ja`→Japanese, `en`→English). Never default to Korean blindly.
- header: a short localized "GitHub Star" label
- question: ask whether they'd like to give this plugin (and the gptaku-plugins marketplace) a GitHub ⭐ to support it — note it is optional and every feature works either way
- options: exactly two — (1) yes, star it → then run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" star yes`; (2) no thanks → then run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" star no`
- If the output contains a line `AUTOUPDATE_ASK <lang>`: ask the user ONCE with AskUserQuestion, written in the language the user is using in this conversation (fall back to <lang> — ko/ja/en — only if the conversation gives no signal). Question: gptaku-plugins can update itself automatically so you always get fixes without running /plugin manually. Turn on auto-update? Options (2): "Turn on auto-update" / "Not now".
  - "Turn on auto-update" → run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" autoupdate yes` (prints `AUTOUPDATE_SET <status>`; on `on`/`already` say it is enabled, otherwise say it could not be changed and point to /plugin → Marketplaces → gptaku-plugins → Turn on auto-update).
  - "Not now" → run `bash "${CLAUDE_PLUGIN_ROOT}/setup/setup.sh" autoupdate no`.
  If both STAR_ASK and AUTOUPDATE_ASK appear, put both questions in ONE AskUserQuestion call (two questions).

If the output is empty, just continue silently. (AskUserQuestion must NOT be in frontmatter allowed-tools.) Do not narrate beyond the question itself.

> **질문 원칙 (shared/questioning-policy.md)**: 리서치 전 범위 좁히기 질문은 추론 가능한 건 묻지 말고 기본값으로 확인하며, 정말 불명확한 것만 묻는다(§1). 이미 구체적인 질문이면 과잉질문 없이 바로 진행(§2c).

# /insane-research Command

인자: `$ARGUMENTS`

**지금 바로** `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-main/SKILL.md`를 Read하고, 그 "인자 해석" 표와 파이프라인을 이 명령의 실행 지시서로 따른다. 참고 자료가 아니라 지금 실행할 절차다.

- 인자 없음 메뉴·스코핑 질문은 **AskUserQuestion 도구를 실제로 호출**한다(채팅 번호 목록으로 대신하지 않는다).
- `query`는 `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-query/SKILL.md`, `refs <주제>`는 `${CLAUDE_PLUGIN_ROOT}/skills/insane-research-refs/SKILL.md`를 읽고 따른다.
- SKILL.md의 `references/…`는 해당 스킬 폴더 기준이다. `references/codex.md`는 Codex 전용이라 읽지 않는다.
