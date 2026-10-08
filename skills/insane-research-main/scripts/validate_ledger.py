#!/usr/bin/env python3
"""
validate_ledger.py — insane-research의 **결정론적 검증 게이트** (control plane이 아니라 단일 체커).

설계 의도 (agent-council B 노선):
  - 오케스트레이션(어디서·어떻게 검색할지)은 LLM/프롬프트(SKILL.md)에 맡긴다.
  - 검증(핵심 주장이 교차검증·반증·1차소스 계약을 통과했는지)은 **코드로 강제**한다.
  - LLM이 status를 자유롭게 쓰는 게 아니라, 이 스크립트가 status를 **계산**한다.

핵심 강제 메커니즘 = "데이터 흐름 락":
  - 이 스크립트만이 `outputs/verified_claims.json`을 생산한다.
  - SKILL.md는 "Phase 5 합성은 verified_claims.json만 근거로 한다"고 계약한다.
  - 따라서 체커를 건너뛰면 합성할 입력 자체가 없다(자기파괴적) → 우회 불가.
  - **exit≠0이면 verified_claims.json을 쓰지 않고 기존 파일도 삭제**한 뒤
    `outputs/gate_failed.json`(차단 사유)을 남긴다 → 실패한 게이트로는 합성 입력이
    존재할 수 없다. (v2.9.0 이전에는 exit 1에서도 verified를 써서 락이 헐거웠다.)
  - 보강: 통과 시 ledger+verified의 sha256 `signature`를 state.json에 기록(위조 불가).

입력:
  <session>/artifacts/claim_ledger.jsonl   (한 줄당 1개 claim record)
  <session>/sources/sources.jsonl          (소스 레지스트리)

출력:
  <session>/outputs/verified_claims.json   (status==verified 만 — 합성 allowlist, exit 0에서만 생성)
  <session>/outputs/unresolved_claims.json (미확정 — annex 전용)
  <session>/outputs/refuted_claims.json    (반증 폐기 — annex 전용)
  <session>/outputs/gate_failed.json       (exit≠0일 때만 — 차단 사유. 통과 시 삭제)
  <session>/state.json 의 "verification" 블록(signature 포함)

종료 코드:
  0  통과 (verified allowlist 생성 완료, 프로세스 위반 없음 — 미확정은 정상)
  1  프로세스 위반 (high-risk 주장에 counter_search 누락 등 → 추가 검색 후 재실행)
  2  하드 에러 (스키마 깨짐·소스 id 미존재·A-E 등급 모순 → 데이터 수정 필요)

claim_ledger.jsonl 레코드 스키마:
  {
    "claim_id": "clm_001",
    "text": "주장 텍스트",
    "risk": "high" | "normal",        # high = 수치/점유율/날짜/법령/인과/재무
    "claim_type": "numeric|legal|causal|descriptive|executable",
    "source_ids": ["src_001", "src_003"],
    "counter_search": "반증 검색 1회 요약 (high-risk 필수, executable은 execution_proof로 대체)",
    "counter_refuted": false,
    "conflicting": false,
    "primary_source": true,
    "execution_proof": {              # claim_type=executable 필수 (없으면 exit 1)
      "script": "재현 스크립트 요약 또는 경로",
      "output": "핵심 출력 발췌",
      "env": "OS/런타임/의존성 버전",
      "verdict": "confirmed|refuted|partial"
    }
  }
  (status / confidence 는 입력에서 신뢰하지 않고 체커가 덮어쓴다.)
"""

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

VALID_GRADES = {"A", "B", "C", "D", "E"}
REQUIRED_CLAIM_FIELDS = ("claim_id", "text", "source_ids")

# 1차 소스로 인정하는 소스 type (sources.jsonl의 type 필드 기준).
# primary_source는 주장 레코드의 자기신고가 아니라 이 집합으로 **파생 계산**한다.
PRIMARY_SOURCE_TYPES = {
    "standards_document",   # PEP/RFC/W3C 등 표준 문서
    "official_docs",        # 공식 문서
    "official_blog",        # 벤더 공식 블로그(1차 발표)
    "official_release",     # 릴리즈 노트
    "government",           # 정부/법령 DB
    "law_db",
    "filing",               # 공시 (SEC/IR)
    "sec_filing",
    "peer_reviewed",        # 피어리뷰 논문
    "primary",              # 명시적 1차 표시
    "repository",           # 코드 저장소 원본 (기계판독 표면)
    "api",                  # 기계판독 API 표면
}

# 서브도메인이 곧 별개 주체인 호스팅 도메인 — org 추론 시 3레이블 유지.
HOSTING_SUFFIXES = {
    "github.io", "gitlab.io", "readthedocs.io", "netlify.app",
    "vercel.app", "pages.dev", "web.app", "blogspot.com",
    "wordpress.com", "substack.com", "hashnode.dev", "notion.site",
}

# 국가 2단 공용 접미사 — org 추론 시 3레이블 유지 (co.kr 등).
SECOND_LEVEL_SUFFIXES = {
    "co.kr", "go.kr", "or.kr", "ac.kr", "re.kr", "pe.kr",
    "co.uk", "ac.uk", "gov.uk", "org.uk",
    "co.jp", "or.jp", "ne.jp", "go.jp", "ac.jp",
    "com.au", "org.au", "com.cn", "com.br", "com.tw",
}


def _read_jsonl(path):
    """JSONL 읽기. (records, errors) 반환."""
    records, errors = [], []
    if not os.path.exists(path):
        return records, [f"파일 없음: {path}"]
    with open(path, "r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                errors.append(f"{os.path.basename(path)}:{lineno} JSON 파싱 실패: {e}")
    return records, errors


def _domain_of(src):
    d = (src.get("domain") or "").strip().lower()
    if d:
        return d
    # domain 없으면 url에서 host 근사 추출
    url = (src.get("url") or "").strip().lower()
    if "://" in url:
        url = url.split("://", 1)[1]
    return url.split("/", 1)[0] if url else ""


def _org_of(src):
    """
    독립성 판정 단위 = 조직(org). 명시적 `org` 필드가 있으면 그것을,
    없으면 호스트에서 등록가능도메인(eTLD+1 근사)을 추론한다.
    peps.python.org와 docs.python.org가 독립 2개로 세어지던 구멍을 막는다.
    """
    org = (src.get("org") or "").strip().lower()
    if org:
        return org
    host = _domain_of(src)
    parts = [p for p in host.split(".") if p]
    if len(parts) <= 2:
        return host
    tail2 = ".".join(parts[-2:])
    if tail2 in HOSTING_SUFFIXES or tail2 in SECOND_LEVEL_SUFFIXES:
        return ".".join(parts[-3:])
    return tail2


def _derived_primary(resolved_sources):
    """primary_source 파생 계산 — 소스 type이 PRIMARY_SOURCE_TYPES에 들면 1차 도달."""
    return any(
        (s.get("type") or "").strip().lower() in PRIMARY_SOURCE_TYPES
        for s in resolved_sources
    )


def _parse_counter(claim):
    """
    counter_search 해석. 반환: (query, urls, legacy_string: bool)
    구조체 {"query": ..., "urls": [...], "summary": ...}만 검증 가능한 형태로 인정.
    """
    c = claim.get("counter_search")
    if isinstance(c, dict):
        query = (c.get("query") or "").strip()
        urls = [u for u in (c.get("urls") or []) if isinstance(u, str) and u.strip()]
        return query, urls, False
    if isinstance(c, str) and c.strip():
        return "", [], True
    return "", [], False


QUOTE_MIN, QUOTE_MAX = 20, 300
_QUOTE_MAP = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "‚": "'",
                            "*": None, "`": None, "#": None})


def _norm_text(s):
    """구절 대조용 정규화 — NFKC·따옴표 직선화·마크다운 기호/링크 제거·공백 1칸·소문자.
    퍼지 매칭은 하지 않는다(날조 구절이 비슷하다는 이유로 통과하면 안 된다)."""
    s = unicodedata.normalize("NFKC", s or "")
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)  # [text](url) → text
    s = s.translate(_QUOTE_MAP)
    return " ".join(s.split()).lower()


def check_evidence(claim, sources_by_id, session_dir, cache):
    """7c~7e: 고위험 주장의 evidence 구절을 저장된 원문 스냅샷과 대조.
    반환: (passed, failed, reasons). cache는 source_id → 정규화된 본문(또는 실패 사유)."""
    passed, failed, reasons = 0, 0, []
    for e in claim.get("evidence") or []:
        sid = e.get("source_id")
        quote = (e.get("quote") or "").strip()
        if not (QUOTE_MIN <= len(quote) <= QUOTE_MAX):
            failed += 1
            reasons.append(f"{sid}: 구절 길이 {len(quote)}자 (허용 {QUOTE_MIN}~{QUOTE_MAX})")
            continue
        if sid not in cache:
            src = sources_by_id.get(sid) or {}
            snap = src.get("snapshot") or {}
            path = os.path.join(session_dir, snap.get("path") or "")
            if snap.get("status") != "ok" or not snap.get("path") or not os.path.isfile(path):
                cache[sid] = (None, f"{sid}: 원문 스냅샷 없음 (status={snap.get('status') or 'missing'})")
            else:
                with open(path, "rb") as f:
                    raw = f.read()
                if snap.get("sha256") and hashlib.sha256(raw).hexdigest() != snap["sha256"]:
                    cache[sid] = (None, f"{sid}: 스냅샷 sha256 불일치 (수집 후 변경됨)")
                else:
                    cache[sid] = (_norm_text(raw.decode("utf-8", errors="replace")), None)
        body, why = cache[sid]
        if body is None:
            failed += 1
            reasons.append(why)
        elif _norm_text(quote) in body:
            passed += 1
        else:
            failed += 1
            reasons.append(f"{sid}: 구절이 원문에 없음 — '{quote[:40]}…'")
    return passed, failed, reasons


def _ledger_schema(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return int(json.load(f).get("ledger_schema") or 1)
    except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
        return 1


def check_source_registry(sources):
    """소스 레지스트리 내부 정합성 검사. (sources_by_id, hard_errors) 반환."""
    hard = []
    sources_by_id = {}
    domain_grades = {}  # domain -> set(grades) : A-E 등급 모순 검출용

    for i, s in enumerate(sources):
        sid = s.get("id")
        if not sid:
            hard.append(f"sources.jsonl[{i}] 'id' 누락")
            continue
        if sid in sources_by_id:
            hard.append(f"sources.jsonl: 중복 source id '{sid}'")
        sources_by_id[sid] = s

        grade = (s.get("quality_rating") or "").strip().upper()
        if grade and grade not in VALID_GRADES:
            hard.append(f"source '{sid}': 잘못된 등급 '{grade}' (A-E만 허용)")
        dom = _domain_of(s)
        if dom and grade in VALID_GRADES:
            domain_grades.setdefault(dom, set()).add(grade)

    # 같은 도메인이 한 run 안에서 서로 다른 등급을 받으면 모순 (예: Gartner B vs C)
    for dom, grades in sorted(domain_grades.items()):
        if len(grades) > 1:
            hard.append(
                f"A-E 등급 모순: 도메인 '{dom}'에 {sorted(grades)} 동시 부여 "
                f"(quality_rubric.md SSOT로 단일화 필요)"
            )
    return sources_by_id, hard


def classify_claim(claim, sources_by_id):
    """
    주장 1건의 status를 결정론적으로 계산.
    반환: (status, reason, process_violation: bool)
      status ∈ {verified, unresolved, refuted}
      process_violation=True → 종료코드 1 유발 (고칠 수 있는 절차 누락)
    """
    ids = claim.get("source_ids") or []
    resolved = [sources_by_id[i] for i in ids if i in sources_by_id]
    orgs = {_org_of(s) for s in resolved if _org_of(s)}
    roots = len(orgs) if orgs else len(resolved)
    grades = {(s.get("quality_rating") or "").strip().upper() for s in resolved}
    high = claim.get("risk") == "high"
    counter_query, _counter_urls, counter_legacy = _parse_counter(claim)

    if claim.get("counter_refuted"):
        return "refuted", "counter-search로 반박됨", False

    # 0) executable 주장: 검색 교차검증 대신 실행 증적(execution_proof)을 강제
    #    (코드로 확정 가능한 주장은 판단이 아니라 실행으로 결판 — ulw-research Phase 3 채용)
    if (claim.get("claim_type") or "").strip().lower() == "executable":
        proof = claim.get("execution_proof")
        verdict = (
            (proof.get("verdict") or "").strip().lower()
            if isinstance(proof, dict)
            else ""
        )
        if not verdict:
            return (
                "unresolved",
                "executable 주장인데 execution_proof 누락 (실행 검증 미수행)",
                True,
            )
        if verdict == "refuted":
            return "refuted", "실행 검증으로 반박됨 (execution_proof.verdict=refuted)", False
        if verdict == "partial":
            return "unresolved", "실행 검증 부분 확인 (partial) — 본문 단정 금지", False
        if verdict == "confirmed":
            if claim.get("conflicting"):
                return "unresolved", "출처 간 충돌 미해소", False
            # 실행 증적이 독립 교차검증을 대체 — 도메인 2개 규칙 미적용
            return "verified", "실행 검증 통과 (execution_proof.verdict=confirmed)", False
        return (
            "unresolved",
            f"execution_proof.verdict 값 불명 '{verdict}' (confirmed|refuted|partial만 허용)",
            True,
        )

    # 1) high-risk인데 반증 검색이 검증 가능한 형태가 아님 → 절차 위반 (코드로 강제하는 CoV)
    #    자유 문자열 한 줄은 수행 여부를 감사할 수 없으므로 구조체를 요구한다.
    if high and counter_legacy:
        return (
            "unresolved",
            "counter_search가 자유 문자열 — 구조체 {query, urls, summary} 필요 (감사 불가)",
            True,
        )
    if high and not counter_query:
        return "unresolved", "high-risk인데 counter_search 누락 (CoV 미수행)", True

    # 2) 독립 출처(조직 기준) 2개 미만 — 서브도메인은 같은 조직으로 센다
    if roots < 2:
        return "unresolved", f"독립 출처(조직) {roots}개 < 2", False

    # 3) 출처 충돌 미해소
    if claim.get("conflicting"):
        return "unresolved", "출처 간 충돌 미해소", False

    # 4) high-risk인데 1차 소스 미도달 — 자기신고가 아니라 소스 type에서 파생 계산
    if high and not _derived_primary(resolved):
        return (
            "unresolved",
            "high-risk인데 1차 소스 미도달 (PRIMARY_SOURCE_TYPES type 소스 없음)",
            False,
        )

    # 5) high-risk인데 B등급 이상 출처가 하나도 없음
    if high and not (grades & {"A", "B"}):
        return "unresolved", "high-risk인데 B등급 이상 출처 없음", False

    # 6) high-risk 다중 표면 — 성격이 같은 표면 2개는 동반 오류를 못 잡는다
    surfaces = {(s.get("type") or "").strip().lower() for s in resolved if s.get("type")}
    if high and len(surfaces) < 2:
        return (
            "unresolved",
            f"high-risk인데 소스 표면(type) {len(surfaces)}종 < 2 (다중 표면 대조 미충족)",
            False,
        )

    return "verified", "ok", False


def validate(ledger_path, sources_path, out_dir, state_path, max_unresolved_ratio=0.5):
    hard_errors = []

    sources, src_parse_errs = _read_jsonl(sources_path)
    hard_errors.extend(src_parse_errs)
    sources_by_id, reg_errs = check_source_registry(sources)
    hard_errors.extend(reg_errs)

    claims, claim_parse_errs = _read_jsonl(ledger_path)
    hard_errors.extend(claim_parse_errs)

    verified, unresolved, refuted = [], [], []
    process_violations = []

    # counter_search.urls 대조용 레지스트리 URL 집합 (슬래시/대소문자 정규화)
    def _norm_url(u):
        return (u or "").strip().lower().rstrip("/")

    registered_urls = {_norm_url(s.get("url")) for s in sources if s.get("url")}

    # v2.10.0 원문 인용 게이트: ledger_schema>=2 세션만 적용 (기존 세션은 이전 규칙)
    enforce_evidence = bool(state_path) and _ledger_schema(state_path) >= 2
    session_dir = os.path.dirname(os.path.dirname(os.path.abspath(sources_path)))
    snapshot_cache = {}

    for i, claim in enumerate(claims):
        # 스키마 하드 검사
        missing = [f for f in REQUIRED_CLAIM_FIELDS if not claim.get(f)]
        if missing:
            hard_errors.append(f"claim[{i}] 필수 필드 누락: {missing}")
            continue
        # 참조 무결성: source_id가 레지스트리에 존재해야 함
        unknown = [i2 for i2 in (claim.get("source_ids") or []) if i2 not in sources_by_id]
        if unknown:
            hard_errors.append(
                f"claim '{claim.get('claim_id')}': 미등록 source id {unknown}"
            )
            continue
        # 참조 무결성: counter_search.urls도 레지스트리에 등록돼 있어야 함
        # (반증 검색을 실제로 했다면 그 결과 소스가 sources.jsonl에 있어야 정상)
        _cq, counter_urls, _legacy = _parse_counter(claim)
        bad_counter_urls = [u for u in counter_urls if _norm_url(u) not in registered_urls]
        if bad_counter_urls:
            hard_errors.append(
                f"claim '{claim.get('claim_id')}': counter_search.urls에 미등록 URL "
                f"{bad_counter_urls} — sources.jsonl에 등록 후 재실행"
            )
            continue

        # 7b: evidence의 source_id는 그 주장의 source_ids 안에 있어야 한다
        if enforce_evidence:
            claim_ids = set(claim.get("source_ids") or [])
            stray = [e.get("source_id") for e in (claim.get("evidence") or [])
                     if e.get("source_id") not in claim_ids]
            if stray:
                hard_errors.append(
                    f"claim '{claim.get('claim_id')}': evidence의 source_id {stray}가 source_ids에 없음"
                )
                continue

        status, reason, violation = classify_claim(claim, sources_by_id)
        evidence_check = None
        is_exec = (claim.get("claim_type") or "").strip().lower() == "executable"
        if (enforce_evidence and status == "verified" and claim.get("risk") == "high"
                and not is_exec):
            if not claim.get("evidence"):
                status, reason = "unresolved", "high-risk인데 evidence 없음 (원문 구절 미제출)"  # 7a
                evidence_check = {"passed": 0, "failed": 0, "reasons": []}
            else:
                ok, bad, why = check_evidence(claim, sources_by_id, session_dir, snapshot_cache)
                evidence_check = {"passed": ok, "failed": bad, "reasons": why}
                if ok == 0:  # 7e
                    status = "unresolved"
                    reason = "high-risk evidence 대조 통과 0건 — " + "; ".join(why[:3])
        record = dict(claim)
        if evidence_check is not None:
            record["evidence_check"] = evidence_check
        record["status"] = status
        record["status_reason"] = reason
        # primary_source는 자기신고를 버리고 파생값으로 덮어쓴다
        resolved_srcs = [
            sources_by_id[sid] for sid in (claim.get("source_ids") or [])
            if sid in sources_by_id
        ]
        record["primary_source"] = _derived_primary(resolved_srcs)
        if status == "verified":
            verified.append(record)
        elif status == "refuted":
            refuted.append(record)
        else:
            unresolved.append(record)
            if violation:
                process_violations.append(f"{claim.get('claim_id')}: {reason}")

    # 하드 에러면 산출물 쓰지 않고 즉시 실패 (exit 2)
    # — 스테일 verified_claims.json이 남아 있으면 실패한 게이트로도 합성이 가능해지므로 삭제한다.
    if hard_errors:
        os.makedirs(out_dir, exist_ok=True)
        _revoke_verified(out_dir, code=2, reasons=hard_errors)
        if state_path and os.path.exists(state_path):
            _stamp_state(
                state_path,
                passed=False,
                signature=None,
                counts=(0, 0, 0),
                unresolved_ratio=None,
                blocked="hard_error",
            )
        _report(hard_errors, [], [], [], [], signature=None, unresolved_ratio=None)
        return 2

    os.makedirs(out_dir, exist_ok=True)
    _write_json(os.path.join(out_dir, "unresolved_claims.json"), unresolved)
    _write_json(os.path.join(out_dir, "refuted_claims.json"), refuted)

    total = len(verified) + len(unresolved) + len(refuted)
    unresolved_ratio = (len(unresolved) / total) if total else 0.0

    # 프로세스 위반이면 합성 allowlist 자체를 만들지 않는다 (데이터 흐름 락).
    if process_violations:
        _revoke_verified(out_dir, code=1, reasons=list(process_violations))
        if state_path and os.path.exists(state_path):
            _stamp_state(
                state_path,
                passed=False,
                signature=None,
                counts=(len(verified), len(unresolved), len(refuted)),
                unresolved_ratio=unresolved_ratio,
                blocked="process_violation",
            )
        _report(
            hard_errors,
            verified,
            unresolved,
            refuted,
            process_violations,
            signature=None,
            unresolved_ratio=unresolved_ratio,
        )
        return 1

    _write_json(os.path.join(out_dir, "verified_claims.json"), verified)
    _clear_gate_marker(out_dir)

    # 서명: verified + 원본 ledger 바이트의 sha256 (체커가 이 데이터로 실제 돌았다는 증거)
    signature = _signature(verified, ledger_path)

    if state_path and os.path.exists(state_path):
        _stamp_state(
            state_path,
            passed=True,
            signature=signature,
            counts=(len(verified), len(unresolved), len(refuted)),
            unresolved_ratio=unresolved_ratio,
        )

    _report(
        hard_errors,
        verified,
        unresolved,
        refuted,
        process_violations,
        signature=signature,
        unresolved_ratio=unresolved_ratio,
        max_unresolved_ratio=max_unresolved_ratio,
    )
    return 0


def _signature(verified, ledger_path):
    h = hashlib.sha256()
    h.update(json.dumps(verified, sort_keys=True, ensure_ascii=False).encode("utf-8"))
    if os.path.exists(ledger_path):
        with open(ledger_path, "rb") as f:
            h.update(f.read())
    return h.hexdigest()


def _write_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _revoke_verified(out_dir, code, reasons):
    """
    게이트 실패 시 합성 allowlist를 실제로 없앤다 (데이터 흐름 락의 본체).

    - 이전 실행이 남긴 스테일 verified_claims.json을 삭제한다.
      (삭제하지 않으면 실패한 게이트로도 합성 입력이 존재해 락이 무력화된다.)
    - 차단 사유를 outputs/gate_failed.json에 남겨 다음 단계가 이유를 읽을 수 있게 한다.
    """
    verified_path = os.path.join(out_dir, "verified_claims.json")
    removed = False
    if os.path.exists(verified_path):
        os.remove(verified_path)
        removed = True
    _write_json(
        os.path.join(out_dir, "gate_failed.json"),
        {
            "exit_code": code,
            "kind": "hard_error" if code == 2 else "process_violation",
            "reasons": list(reasons),
            "verified_claims_removed": removed,
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "checker": "validate_ledger.py",
            "next_step": (
                "데이터(스키마/소스 id/등급)를 고치고 재실행"
                if code == 2
                else "누락된 counter_search·execution_proof를 수행해 ledger 갱신 후 재실행"
            ),
        },
    )
    return removed


def _clear_gate_marker(out_dir):
    """통과 시 이전 실패 마커를 제거한다 (스테일 차단 상태 방지)."""
    marker = os.path.join(out_dir, "gate_failed.json")
    if os.path.exists(marker):
        os.remove(marker)


def _stamp_state(
    state_path, passed, signature, counts, unresolved_ratio=None, blocked=None
):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        return
    state["verification"] = {
        "passed": passed,
        "signature": signature,
        "verified_count": counts[0],
        "unresolved_count": counts[1],
        "refuted_count": counts[2],
        "unresolved_ratio": (
            round(unresolved_ratio, 4) if unresolved_ratio is not None else None
        ),
        "blocked": blocked,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checker": "validate_ledger.py",
    }
    # atomic write: temp → rename
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, state_path)


def _report(
    hard_errors,
    verified,
    unresolved,
    refuted,
    process_violations,
    signature,
    unresolved_ratio=None,
    max_unresolved_ratio=0.5,
):
    out = sys.stderr
    print("=== validate_ledger 결과 ===", file=out)
    if hard_errors:
        print(f"\n[HARD ERROR] {len(hard_errors)}건 — 데이터 수정 후 재실행 (exit 2):", file=out)
        for e in hard_errors:
            print(f"  - {e}", file=out)
        print(
            "  → verified_claims.json 폐기·gate_failed.json 기록. 합성 입력 없음.",
            file=out,
        )
        return
    ratio_txt = (
        f"  unresolved_ratio={unresolved_ratio:.0%}" if unresolved_ratio is not None else ""
    )
    print(
        f"  verified={len(verified)}  unresolved={len(unresolved)}  refuted={len(refuted)}"
        f"{ratio_txt}",
        file=out,
    )
    if (
        not process_violations
        and unresolved_ratio is not None
        and unresolved_ratio > max_unresolved_ratio
    ):
        print(
            f"  [WARN] 미확정 비율 {unresolved_ratio:.0%} > {max_unresolved_ratio:.0%} — "
            f"통과했지만 근거가 얕다. 보강 검색을 권장한다.",
            file=out,
        )
    if process_violations:
        print(
            f"\n[FAIL] 프로세스 위반 {len(process_violations)}건 (exit 1) — "
            f"누락 절차(counter_search 또는 execution_proof) 수행 후 ledger 갱신·재실행:",
            file=out,
        )
        for v in process_violations:
            print(f"  - {v}", file=out)
        print(
            "  → verified_claims.json 폐기·gate_failed.json 기록. "
            "게이트를 통과시키기 전에는 합성 금지(입력 없음).",
            file=out,
        )
    else:
        print("  → 통과. 합성은 outputs/verified_claims.json 만 근거로 진행.", file=out)
        if signature:
            print(f"  signature={signature[:16]}…", file=out)


def _resolve_paths(args):
    if args.session:
        base = args.session
        ledger = args.ledger or os.path.join(base, "artifacts", "claim_ledger.jsonl")
        sources = args.sources or os.path.join(base, "sources", "sources.jsonl")
        out_dir = args.out_dir or os.path.join(base, "outputs")
        state = args.state or os.path.join(base, "state.json")
    else:
        ledger = args.ledger
        sources = args.sources
        out_dir = args.out_dir or "."
        state = args.state
        if not (ledger and sources):
            raise SystemExit("--session 또는 (--ledger AND --sources) 가 필요합니다.")
    return ledger, sources, out_dir, state


def main():
    p = argparse.ArgumentParser(description="insane-research 결정론적 검증 게이트")
    p.add_argument("--session", help="리서치 세션 폴더 (RESEARCH/{topic}_{ts})")
    p.add_argument("--ledger", help="claim_ledger.jsonl 경로 (override)")
    p.add_argument("--sources", help="sources.jsonl 경로 (override)")
    p.add_argument("--out-dir", help="출력 폴더 (기본: <session>/outputs)")
    p.add_argument("--state", help="state.json 경로 (기본: <session>/state.json)")
    p.add_argument(
        "--max-unresolved-ratio",
        type=float,
        default=0.5,
        help="미확정 비율 경고 임계치 (기본 0.5). 초과해도 exit code는 바뀌지 않는다.",
    )
    args = p.parse_args()

    ledger, sources, out_dir, state = _resolve_paths(args)
    sys.exit(validate(ledger, sources, out_dir, state, args.max_unresolved_ratio))


if __name__ == "__main__":
    main()
