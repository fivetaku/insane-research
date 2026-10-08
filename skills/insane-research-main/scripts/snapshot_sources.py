#!/usr/bin/env python3
"""snapshot_sources.py — 고위험 주장이 인용한 출처의 원문을 저장한다 (v2.10.0).

validate_ledger.py의 원문 인용 게이트(7c~7e)가 evidence 구절을 대조할 원문을 만든다.
WebFetch는 모델이 요약한 글을 돌려주므로 원문 대조에 쓸 수 없다 — insane-search
엔진으로 직접 받는다.

입력:  <session>/artifacts/claim_ledger.jsonl, <session>/sources/sources.jsonl
출력:  <session>/sources/snapshots/<id>.txt
       sources.jsonl 각 대상 레코드에 snapshot{path, sha256, chars, status, fetched_at, via}

대상: risk=high 주장의 source_ids에 든 출처만 (호출량 억제). 이미 status=ok인 출처는
재수집하지 않는다(해시 고정 — 게이트는 수집 시점 원문으로 대조한다).

status: ok | blocked(엔진 실패) | too_large(텍스트 2MB 초과) | error(예외)

엔진 위치: --engine-dir > $INSANE_SEARCH_ENGINE_DIR > 플러그인 캐시 최신 버전 탐색.
종료 코드: 0 완료(일부 blocked여도 0 — 게이트가 판정), 2 입력/엔진 없음.
"""

import argparse
import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

MAX_BYTES_DEFAULT = 2 * 1024 * 1024


def _read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def _find_engine_dir(explicit):
    if explicit:
        return explicit
    env = os.environ.get("INSANE_SEARCH_ENGINE_DIR")
    if env:
        return env
    pattern = os.path.expanduser("~/.claude/plugins/cache/*/insane-search/*/skills/insane-search")
    found = sorted(glob.glob(pattern), key=lambda p: [int(x) if x.isdigit() else -1
                                                      for x in p.split("/")[-3].split(".")])
    return found[-1] if found else None


def _load_fetch(engine_dir):
    if not engine_dir or not os.path.isdir(os.path.join(engine_dir, "engine")):
        return None
    sys.path.insert(0, engine_dir)
    try:
        from engine import fetch  # type: ignore  # noqa: E402
    except Exception as e:  # pragma: no cover - 환경 문제 보고용
        print(f"엔진 import 실패: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    return fetch


def target_ids(claims):
    ids = []
    for c in claims:
        if c.get("risk") != "high":
            continue
        for sid in c.get("source_ids") or []:
            if sid not in ids:
                ids.append(sid)
    return ids


def snapshot(session, fetch, max_bytes=MAX_BYTES_DEFAULT, timeout=25):
    sources_path = os.path.join(session, "sources", "sources.jsonl")
    sources = _read_jsonl(sources_path)
    claims = _read_jsonl(os.path.join(session, "artifacts", "claim_ledger.jsonl"))
    by_id = {s.get("id"): s for s in sources}
    snap_dir = os.path.join(session, "sources", "snapshots")
    os.makedirs(snap_dir, exist_ok=True)

    counts = {"ok": 0, "blocked": 0, "too_large": 0, "error": 0, "skipped": 0}
    for sid in target_ids(claims):
        src = by_id.get(sid)
        if not src or not src.get("url"):
            continue
        prev = src.get("snapshot") or {}
        if prev.get("status") == "ok" and os.path.isfile(os.path.join(session, prev.get("path", ""))):
            counts["skipped"] += 1
            continue
        rel = f"sources/snapshots/{sid}.txt"
        rec: dict = {"path": rel, "fetched_at": datetime.now(timezone.utc).isoformat()}
        try:
            r = fetch(src["url"], timeout=timeout)
            text = getattr(r, "content", "") or ""
            rec["via"] = getattr(r, "extraction_source", "") or getattr(r, "verdict", "") or ""
            if not getattr(r, "ok", False) or not text.strip():
                rec["status"] = "blocked"
            else:
                data = text.encode("utf-8")
                if len(data) > max_bytes:
                    rec["status"] = "too_large"
                    rec["chars"] = len(text)
                else:
                    with open(os.path.join(session, rel), "wb") as f:
                        f.write(data)
                    rec.update(status="ok", chars=len(text), sha256=hashlib.sha256(data).hexdigest())
        except Exception as e:
            rec["status"] = "error"
            rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
        src["snapshot"] = rec
        counts[rec["status"]] += 1

    tmp = sources_path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for s in sources:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
    os.replace(tmp, sources_path)
    return counts


def main():
    p = argparse.ArgumentParser(description="고위험 주장 인용 출처의 원문 스냅샷 저장")
    p.add_argument("--session", required=True)
    p.add_argument("--engine-dir", help="insane-search 스킬 디렉터리 (engine/ 패키지를 담은 곳)")
    p.add_argument("--max-bytes", type=int, default=MAX_BYTES_DEFAULT)
    p.add_argument("--timeout", type=int, default=25)
    args = p.parse_args()

    for rel in ("sources/sources.jsonl", "artifacts/claim_ledger.jsonl"):
        if not os.path.exists(os.path.join(args.session, rel)):
            print(f"입력 없음: {rel}", file=sys.stderr)
            return 2
    fetch = _load_fetch(_find_engine_dir(args.engine_dir))
    if fetch is None:
        print("insane-search 엔진을 찾지 못함 — --engine-dir 또는 INSANE_SEARCH_ENGINE_DIR 지정", file=sys.stderr)
        return 2

    c = snapshot(args.session, fetch, args.max_bytes, args.timeout)
    print("=== snapshot_sources ===", file=sys.stderr)
    print(f"  ok={c['ok']} blocked={c['blocked']} too_large={c['too_large']} error={c['error']} "
          f"skipped(기존 ok)={c['skipped']}", file=sys.stderr)
    if c["blocked"] + c["too_large"] + c["error"]:
        print("  [warn] 스냅샷 없는 출처만으로 뒷받침되는 고위험 주장은 게이트에서 unresolved가 된다.",
              file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
