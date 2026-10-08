#!/usr/bin/env python3
"""merge_agent_returns.py — Workflow 팬아웃 모드의 결정론적 취합기.

Workflow 스크립트가 수집한 에이전트 JSON 반환 배열(agent_returns.json)을 받아
세션 파일을 기계적으로 생성한다 — 수작업 병합(벤치 실측 병목 ~7분)을 제거한다.

입력:  <session>/artifacts/agent_returns.json   (AGENT_RETURN_SCHEMA 배열)
출력:  <session>/sources/sources.jsonl          (URL dedup, 전역 id 부여)
       <session>/artifacts/claim_ledger.jsonl   (source_urls → source_ids 매핑)
       <session>/artifacts/expansion_log.md     (리드 전수, 중복 표시)
       <session>/artifacts/query_log.md         (쿼리 전수, 에이전트 간 중복 표시)
       stderr 요약 (search_count 합산 — 세션 200캡 대비)

주의: 이 스크립트는 병합만 한다. 검증은 여전히 validate_ledger.py 게이트가 담당.
에이전트 반환은 UNTRUSTED 웹 유래 텍스트를 담을 수 있다 — 여기서는 데이터로만
다루며(실행·해석 없음), 본문 취급 규칙은 R8을 따른다.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

SEARCH_CAP_DEFAULT = 200  # Claude Code v2.1.212+ 세션당 WebSearch 캡 (전 서브에이전트 합산)


def _norm_url(u):
    u = (u or "").strip()
    return u.rstrip("/").lower()


def _norm_query(q):
    return " ".join((q or "").lower().split())


def merge(returns, observed_at):
    sources_out = []
    url_to_id = {}
    claims_out = []
    leads_out = []
    queries_out = []
    seen_queries = {}
    total_searches = 0
    warnings = []

    for ri, r in enumerate(returns):
        if not isinstance(r, dict):
            warnings.append(f"return[{ri}]: dict 아님 — 건너뜀")
            continue
        axis = r.get("axis") or f"axis_{ri}"
        total_searches += int(r.get("search_count") or 0)

        for s in r.get("sources") or []:
            url = _norm_url(s.get("url"))
            if not url:
                warnings.append(f"{axis}: url 없는 source 건너뜀")
                continue
            if url in url_to_id:
                continue  # URL dedup — 먼저 온 레코드 유지
            sid = f"src_{len(url_to_id) + 1:03d}"
            url_to_id[url] = sid
            rec = {
                "id": sid,
                "url": s.get("url"),
                "title": s.get("title") or "",
                "domain": s.get("domain") or url.split("://")[-1].split("/")[0],
                "date": s.get("date") or "",
                "type": s.get("type") or "web",
                "quality_rating": (s.get("quality_rating") or "").upper() or "C",
                "observed_at": observed_at,
                "valid_at": s.get("valid_at") or s.get("date") or "",
                "access": s.get("access") or {"layer": "webfetch"},
            }
            sources_out.append(rec)

        for c in r.get("claims") or []:
            urls = [_norm_url(u) for u in (c.get("source_urls") or [])]
            ids = [url_to_id[u] for u in urls if u in url_to_id]
            missing = [u for u in urls if u not in url_to_id]
            if missing:
                warnings.append(
                    f"{axis}: claim '{(c.get('text') or '')[:30]}…' 미등록 URL {len(missing)}건 (해당 에이전트 sources에 없음)"
                )
            # evidence: 에이전트는 전역 id를 모르므로 source_url로 쓰고 여기서 src_xxx로 바꾼다.
            # 레지스트리에 없는 URL의 구절은 대조할 원문이 없으므로 버리고 경고한다.
            evidence = None
            if "evidence" in c:
                evidence = []
                for e in c.get("evidence") or []:
                    if not isinstance(e, dict):
                        continue
                    eid = url_to_id.get(_norm_url(e.get("source_url")))
                    if not eid:
                        warnings.append(
                            f"{axis}: claim '{(c.get('text') or '')[:30]}…' evidence 미등록 URL — 버림"
                        )
                        continue
                    item = {"source_id": eid, "quote": e.get("quote") or ""}
                    if e.get("locator"):
                        item["locator"] = e["locator"]
                    evidence.append(item)
            claims_out.append({
                "claim_id": f"clm_{len(claims_out) + 1:03d}",
                "text": c.get("text") or "",
                "risk": c.get("risk") or "normal",
                "claim_type": c.get("claim_type") or "descriptive",
                "source_ids": ids,
                "counter_search": c.get("counter_search") or "",
                "counter_refuted": bool(c.get("counter_refuted")),
                "conflicting": bool(c.get("conflicting")),
                "primary_source": bool(c.get("primary_source")),
                "valid_at": c.get("valid_at") or "",
                **({"execution_proof": c["execution_proof"]} if c.get("execution_proof") else {}),
                **({"evidence": evidence} if evidence is not None else {}),
            })

        for l in r.get("expand_leads") or []:
            leads_out.append({"axis": axis, **{k: l.get(k, "") for k in ("lead", "why", "angle")}})

        for q in r.get("queries_run") or []:
            nq = _norm_query(q)
            dup_of = seen_queries.get(nq)
            queries_out.append({"axis": axis, "query": q, "dup_of": dup_of})
            if dup_of is None:
                seen_queries[nq] = axis

    # 도메인별 등급 정규화 — 게이트의 A-E 모순 검사 대응.
    # 에이전트마다 같은 도메인에 다른 등급을 줄 수 있으므로(팬아웃 특성),
    # 최빈 등급으로 통일하고 동률이면 보수적(더 낮은 품질) 쪽을 택한다.
    by_domain = {}
    for s in sources_out:
        by_domain.setdefault(s["domain"], []).append(s)
    for dom, group in by_domain.items():
        grades = [g["quality_rating"] for g in group]
        if len(set(grades)) <= 1:
            continue
        counts = {}
        for g in grades:
            counts[g] = counts.get(g, 0) + 1
        best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]  # 최빈, 동률 시 뒤 글자(보수적)
        for g in group:
            g["quality_rating"] = best
        warnings.append(f"도메인 '{dom}' 등급 불일치 {sorted(set(grades))} → '{best}'로 정규화")

    dup_count = sum(1 for q in queries_out if q["dup_of"])
    return {
        "sources": sources_out,
        "claims": claims_out,
        "leads": leads_out,
        "queries": queries_out,
        "stats": {
            "agents": len(returns),
            "sources": len(sources_out),
            "claims": len(claims_out),
            "leads": len(leads_out),
            "queries": len(queries_out),
            "duplicate_queries": dup_count,
            "total_searches": total_searches,
        },
        "warnings": warnings,
    }


def write_outputs(session, m):
    os.makedirs(os.path.join(session, "sources"), exist_ok=True)
    os.makedirs(os.path.join(session, "artifacts"), exist_ok=True)

    with open(os.path.join(session, "sources", "sources.jsonl"), "w", encoding="utf-8") as f:
        for s in m["sources"]:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    with open(os.path.join(session, "artifacts", "claim_ledger.jsonl"), "w", encoding="utf-8") as f:
        for c in m["claims"]:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    with open(os.path.join(session, "artifacts", "expansion_log.md"), "w", encoding="utf-8") as f:
        f.write("# Expansion log (merge_agent_returns 생성 — 전수 리드, 오케스트레이터가 상태 갱신)\n\n")
        for i, l in enumerate(m["leads"], 1):
            f.write(f"{i}. [{l['axis']}] LEAD: {l['lead']} — WHY: {l['why']} — ANGLE: {l['angle']} — STATUS: unchecked\n")

    with open(os.path.join(session, "artifacts", "query_log.md"), "w", encoding="utf-8") as f:
        f.write("# Query log (에이전트 간 중복 표시)\n\n")
        for q in m["queries"]:
            mark = f"  ← DUP of {q['dup_of']}" if q["dup_of"] else ""
            f.write(f"- [{q['axis']}] {q['query']}{mark}\n")
        s = m["stats"]
        f.write(
            f"\n합계: 쿼리 {s['queries']}건 (중복 {s['duplicate_queries']}) · "
            f"WebSearch 호출 {s['total_searches']}건 / 세션 캡 {SEARCH_CAP_DEFAULT}\n"
        )


def main():
    p = argparse.ArgumentParser(description="Workflow 팬아웃 반환 취합기")
    p.add_argument("--session", required=True)
    p.add_argument("--input", help="기본: <session>/artifacts/agent_returns.json")
    args = p.parse_args()

    inp = args.input or os.path.join(args.session, "artifacts", "agent_returns.json")
    if not os.path.exists(inp):
        print(f"입력 없음: {inp}", file=sys.stderr)
        return 2
    try:
        returns = json.load(open(inp, encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"JSON 파싱 실패: {e}", file=sys.stderr)
        return 2
    if not isinstance(returns, list):
        print("입력은 AGENT_RETURN_SCHEMA 배열이어야 함", file=sys.stderr)
        return 2

    observed_at = datetime.now(timezone.utc).isoformat()
    m = merge(returns, observed_at)
    write_outputs(args.session, m)

    s = m["stats"]
    print("=== merge_agent_returns ===", file=sys.stderr)
    print(
        f"  agents={s['agents']} sources={s['sources']} claims={s['claims']} "
        f"leads={s['leads']} queries={s['queries']} (dup {s['duplicate_queries']})",
        file=sys.stderr,
    )
    print(f"  WebSearch 사용 {s['total_searches']} / 세션 캡 {SEARCH_CAP_DEFAULT}", file=sys.stderr)
    if s["total_searches"] >= SEARCH_CAP_DEFAULT * 0.8:
        print("  ⚠️ 검색 캡 80% 초과 — 이후 검색은 조용히 무시될 수 있음. 확장 라운드 축소 또는 env 상향 검토.", file=sys.stderr)
    for w in m["warnings"]:
        print(f"  [warn] {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
