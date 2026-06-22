#!/usr/bin/env python3
"""
eval_report.py — insane-research **결정론적 평가 채점기** (측정 도구, 게이트 아님).

목적: 검증 게이트(validate_ledger.py)가 "진짜 효과 있는지"를 숫자로 재기 위한 계측기.
LLM judge 없이 코드로 계산 가능한 4개 지표만 측정한다 → 재현 가능, A/B 비교 가능.

지표:
  1. citation_resolution_rate — 본문의 인용 토큰(src_xxx) 중 sources 레지스트리에 존재하는 비율
                                 (dangling citation = 깨진 인용 = 환각 신호)
  2. orphan_source_rate       — 레지스트리에 있으나 본문에서 한 번도 인용 안 된 소스 비율
  3. leak_rate                — unresolved/refuted 주장이 본문에 단정형으로 샌 비율
                                 (verified-only 합성 게이트가 지켜졌는가 = 게이트의 핵심 효과)
  4. verified_coverage_rate   — verified 주장 중 본문에 실제로 인용/등장한 비율
                                 (합성이 allowlist를 실제로 소비했는가)

입력 (세션 폴더):
  <session>/outputs/**/*.md                 (합성된 보고서 본문)
  <session>/sources/sources.jsonl           (소스 레지스트리)
  <session>/outputs/verified_claims.json    (validate_ledger 산출)
  <session>/outputs/unresolved_claims.json
  <session>/outputs/refuted_claims.json

출력:
  <session>/outputs/eval_report.json + stderr 요약

판정(verdict): leak 또는 dangling citation이 1건이라도 있으면 FAIL(exit 1), 아니면 PASS(exit 0).
  → 측정 도구지만, 명백한 결함(인용 깨짐·미검증 누출)은 회귀로 간주해 비0 종료.
"""

import argparse
import glob
import json
import os
import re
import sys

SRC_TOKEN = re.compile(r"src_[0-9a-zA-Z_]+")
NGRAM = 6  # leak/coverage 판별용 content char n-gram 길이


def _read_jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def _read_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return []


def _load_body(out_dir):
    """outputs/ 아래 모든 .md를 본문으로 합친다."""
    parts = []
    for p in sorted(glob.glob(os.path.join(out_dir, "**", "*.md"), recursive=True)):
        with open(p, "r", encoding="utf-8") as f:
            parts.append(f.read())
    return "\n".join(parts)


def _content(s):
    """공백·구두점 제거한 content 문자열(한글/영숫자/%만 유지) — 조사·띄어쓰기 흔들림 흡수."""
    return re.sub(r"[^0-9A-Za-z가-힣%]", "", s or "")


def _ngrams(s, n=NGRAM):
    return {s[i:i + n] for i in range(len(s) - n + 1)} if len(s) >= n else set()


def _claim_present(claim_text, claim_id, body_blob, body_raw, exclude_blob=""):
    """주장이 본문에 등장하는가? claim_id 직접 등장 OR (exclude에 없는) 특징 n-gram이 본문에 등장.
    exclude_blob(예: verified 주장 본문)에 있는 n-gram은 공유 맥락(버전번호 등)이므로 제외 → 오탐 방지."""
    if claim_id and claim_id in body_raw:
        return True
    grams = _ngrams(_content(claim_text)) - _ngrams(exclude_blob)
    return any(g in body_blob for g in grams)


def evaluate(out_dir, sources_path):
    body = _load_body(out_dir)
    body_blob = _content(body)
    sources = _read_jsonl(sources_path)
    source_ids = {s.get("id") for s in sources if s.get("id")}
    verified = _read_json(os.path.join(out_dir, "verified_claims.json"))
    unresolved = _read_json(os.path.join(out_dir, "unresolved_claims.json"))
    refuted = _read_json(os.path.join(out_dir, "refuted_claims.json"))

    # 1) citation resolution
    cited = SRC_TOKEN.findall(body)
    cited_set = set(cited)
    dangling = sorted(c for c in cited_set if c not in source_ids)
    resolved = sorted(c for c in cited_set if c in source_ids)
    cite_rate = (len(resolved) / len(cited_set)) if cited_set else 1.0

    # 2) orphan sources (레지스트리에 있으나 본문 미인용)
    orphans = sorted(sid for sid in source_ids if sid not in cited_set)
    orphan_rate = (len(orphans) / len(source_ids)) if source_ids else 0.0

    # verified 주장 본문 = 공유 맥락(버전번호·고유명사 등). leak 판별 시 이 n-gram은 제외.
    verified_blob = _content(" ".join(c.get("text", "") for c in verified))

    # 3) leak: unresolved/refuted 주장이 본문에 단정형으로 샜는가
    leaks = []
    for claim in unresolved + refuted:
        cid = claim.get("claim_id", "")
        text = claim.get("text", "")
        if _claim_present(text, cid, body_blob, body, exclude_blob=verified_blob):
            leaks.append({"claim_id": cid, "text": text, "status": claim.get("status")})
    pool = len(unresolved) + len(refuted)
    leak_rate = (len(leaks) / pool) if pool else 0.0

    # 4) verified coverage (allowlist가 실제로 본문에 쓰였는가) — 직접 매칭(제외 없음)
    covered = sum(
        1 for c in verified
        if _claim_present(c.get("text", ""), c.get("claim_id", ""), body_blob, body)
    )
    cov_rate = (covered / len(verified)) if verified else 1.0

    verdict = "PASS" if (not leaks and not dangling) else "FAIL"
    report = {
        "verdict": verdict,
        "metrics": {
            "citation_resolution_rate": round(cite_rate, 3),
            "orphan_source_rate": round(orphan_rate, 3),
            "leak_rate": round(leak_rate, 3),
            "verified_coverage_rate": round(cov_rate, 3),
        },
        "counts": {
            "citations_total": len(cited_set),
            "citations_dangling": len(dangling),
            "sources_total": len(source_ids),
            "orphan_sources": len(orphans),
            "verified": len(verified),
            "unresolved": len(unresolved),
            "refuted": len(refuted),
            "leaks": len(leaks),
        },
        "dangling_citations": dangling,
        "orphan_sources": orphans,
        "leaks": leaks,
    }
    return report


def _print(report):
    m, c = report["metrics"], report["counts"]
    out = sys.stderr
    print("=== eval_report 결과 ===", file=out)
    print(f"  verdict: {report['verdict']}", file=out)
    print(
        f"  citation_resolution={m['citation_resolution_rate']:.0%} "
        f"(dangling {c['citations_dangling']}/{c['citations_total']})",
        file=out,
    )
    print(
        f"  leak_rate={m['leak_rate']:.0%} (미검증 누출 {c['leaks']}/{c['unresolved']+c['refuted']})",
        file=out,
    )
    print(
        f"  orphan_source_rate={m['orphan_source_rate']:.0%} ({c['orphan_sources']}/{c['sources_total']})",
        file=out,
    )
    print(f"  verified_coverage={m['verified_coverage_rate']:.0%}", file=out)
    if report["leaks"]:
        print("  [LEAK] 미검증/반박 주장이 본문에 등장:", file=out)
        for lk in report["leaks"]:
            print(f"    - {lk['claim_id']} ({lk['status']}): {lk['text'][:50]}", file=out)
    if report["dangling_citations"]:
        print(f"  [DANGLING] 레지스트리에 없는 인용: {report['dangling_citations']}", file=out)


def main():
    p = argparse.ArgumentParser(description="insane-research 결정론적 평가 채점기")
    p.add_argument("--session", required=True, help="리서치 세션 폴더")
    p.add_argument("--out-dir", help="기본: <session>/outputs")
    p.add_argument("--sources", help="기본: <session>/sources/sources.jsonl")
    args = p.parse_args()
    out_dir = args.out_dir or os.path.join(args.session, "outputs")
    sources = args.sources or os.path.join(args.session, "sources", "sources.jsonl")

    report = evaluate(out_dir, sources)
    with open(os.path.join(out_dir, "eval_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    _print(report)
    sys.exit(0 if report["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
