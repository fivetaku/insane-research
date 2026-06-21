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
  - 보강: 통과 시 ledger+verified의 sha256 `signature`를 state.json에 기록(위조 불가).

입력:
  <session>/artifacts/claim_ledger.jsonl   (한 줄당 1개 claim record)
  <session>/sources/sources.jsonl          (소스 레지스트리)

출력:
  <session>/outputs/verified_claims.json   (status==verified 만 — 합성 allowlist)
  <session>/outputs/unresolved_claims.json (미확정 — annex 전용)
  <session>/outputs/refuted_claims.json    (반증 폐기 — annex 전용)
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
    "claim_type": "numeric|legal|causal|descriptive",
    "source_ids": ["src_001", "src_003"],
    "counter_search": "반증 검색 1회 요약 (high-risk 필수)",
    "counter_refuted": false,
    "conflicting": false,
    "primary_source": true
  }
  (status / confidence 는 입력에서 신뢰하지 않고 체커가 덮어쓴다.)
"""

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

VALID_GRADES = {"A", "B", "C", "D", "E"}
REQUIRED_CLAIM_FIELDS = ("claim_id", "text", "source_ids")


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
    domains = {_domain_of(s) for s in resolved if _domain_of(s)}
    roots = len(domains) if domains else len(resolved)
    grades = {(s.get("quality_rating") or "").strip().upper() for s in resolved}
    high = claim.get("risk") == "high"
    counter = (claim.get("counter_search") or "").strip()

    if claim.get("counter_refuted"):
        return "refuted", "counter-search로 반박됨", False

    # 1) high-risk인데 반증 검색 자체를 안 함 → 절차 위반 (코드로 강제하는 CoV)
    if high and not counter:
        return "unresolved", "high-risk인데 counter_search 누락 (CoV 미수행)", True

    # 2) 독립 출처(도메인 기준) 2개 미만
    if roots < 2:
        return "unresolved", f"독립 출처(도메인) {roots}개 < 2", False

    # 3) 출처 충돌 미해소
    if claim.get("conflicting"):
        return "unresolved", "출처 간 충돌 미해소", False

    # 4) high-risk인데 1차 소스 미도달
    if high and not claim.get("primary_source"):
        return "unresolved", "high-risk인데 primary_source=false", False

    # 5) high-risk인데 B등급 이상 출처가 하나도 없음
    if high and not (grades & {"A", "B"}):
        return "unresolved", "high-risk인데 B등급 이상 출처 없음", False

    return "verified", "ok", False


def validate(ledger_path, sources_path, out_dir, state_path):
    hard_errors = []

    sources, src_parse_errs = _read_jsonl(sources_path)
    hard_errors.extend(src_parse_errs)
    sources_by_id, reg_errs = check_source_registry(sources)
    hard_errors.extend(reg_errs)

    claims, claim_parse_errs = _read_jsonl(ledger_path)
    hard_errors.extend(claim_parse_errs)

    verified, unresolved, refuted = [], [], []
    process_violations = []

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

        status, reason, violation = classify_claim(claim, sources_by_id)
        record = dict(claim)
        record["status"] = status
        record["status_reason"] = reason
        if status == "verified":
            verified.append(record)
        elif status == "refuted":
            refuted.append(record)
        else:
            unresolved.append(record)
            if violation:
                process_violations.append(
                    f"  - {claim.get('claim_id')}: {reason}"
                )

    # 하드 에러면 산출물 쓰지 않고 즉시 실패 (exit 2)
    if hard_errors:
        _report(hard_errors, [], [], [], [], signature=None)
        return 2

    os.makedirs(out_dir, exist_ok=True)
    _write_json(os.path.join(out_dir, "verified_claims.json"), verified)
    _write_json(os.path.join(out_dir, "unresolved_claims.json"), unresolved)
    _write_json(os.path.join(out_dir, "refuted_claims.json"), refuted)

    # 서명: verified + 원본 ledger 바이트의 sha256 (체커가 이 데이터로 실제 돌았다는 증거)
    signature = _signature(verified, ledger_path)

    if state_path and os.path.exists(state_path):
        _stamp_state(
            state_path,
            passed=not process_violations,
            signature=signature,
            counts=(len(verified), len(unresolved), len(refuted)),
        )

    _report(
        hard_errors,
        verified,
        unresolved,
        refuted,
        process_violations,
        signature=signature,
    )
    return 1 if process_violations else 0


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


def _stamp_state(state_path, passed, signature, counts):
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
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "checker": "validate_ledger.py",
    }
    # atomic write: temp → rename
    tmp = state_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, state_path)


def _report(hard_errors, verified, unresolved, refuted, process_violations, signature):
    out = sys.stderr
    print("=== validate_ledger 결과 ===", file=out)
    if hard_errors:
        print(f"\n[HARD ERROR] {len(hard_errors)}건 — 데이터 수정 후 재실행 (exit 2):", file=out)
        for e in hard_errors:
            print(f"  - {e}", file=out)
        return
    print(
        f"  verified={len(verified)}  unresolved={len(unresolved)}  refuted={len(refuted)}",
        file=out,
    )
    if process_violations:
        print(
            f"\n[FAIL] high-risk 주장 {len(process_violations)}건이 counter_search 누락 "
            f"(exit 1) — 반증 검색 수행 후 ledger 갱신·재실행:",
            file=out,
        )
        for v in process_violations:
            print(v, file=out)
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
    args = p.parse_args()

    ledger, sources, out_dir, state = _resolve_paths(args)
    sys.exit(validate(ledger, sources, out_dir, state))


if __name__ == "__main__":
    main()
