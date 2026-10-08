"""merge_agent_returns.py 취합기 계약 테스트 — 병합 결과가 validate_ledger 게이트에 그대로 물리는지까지."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "insane-research-main" / "scripts"


def run_merge(session):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "merge_agent_returns.py"), "--session", str(session)],
        capture_output=True,
        text=True,
    )


def make_session(tmp_path, returns):
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "artifacts" / "agent_returns.json").write_text(
        json.dumps(returns, ensure_ascii=False), encoding="utf-8"
    )
    (tmp_path / "state.json").write_text('{"session_id": "t", "progress": {}}', encoding="utf-8")
    return tmp_path


RET_A = {
    "axis": "redis",
    "sources": [
        {"url": "https://a.example.com/x", "title": "A", "domain": "a.example.com", "type": "official_docs", "quality_rating": "A", "date": "2026-06-01"},
        {"url": "https://b.example.org/y", "title": "B", "domain": "b.example.org", "type": "independent_benchmark", "quality_rating": "B", "date": "2026-06-02"},
    ],
    "claims": [
        {"text": "사실1", "risk": "high", "claim_type": "numeric",
         "source_urls": ["https://a.example.com/x", "https://b.example.org/y"],
         "counter_search": {"query": "사실1 반증 2026", "urls": [], "summary": "반증 없음"},
         "primary_source": True, "valid_at": "2026-06-01"}
    ],
    "expand_leads": [{"lead": "리드1", "why": "이유", "angle": "각도"}],
    "queries_run": ["redis license 2026", "site:redis.io agpl"],
    "search_count": 8,
}
RET_B = {
    "axis": "valkey",
    "sources": [
        {"url": "https://a.example.com/x/", "title": "A dup(슬래시)", "domain": "a.example.com", "quality_rating": "A"},
        {"url": "https://c.example.net/z", "title": "C", "domain": "c.example.net", "quality_rating": "B"},
    ],
    "claims": [],
    "expand_leads": [],
    "queries_run": ["REDIS  license  2026"],
    "search_count": 5,
}


def test_merge_dedup_and_outputs(tmp_path):
    s = make_session(tmp_path, [RET_A, RET_B])
    r = run_merge(s)
    assert r.returncode == 0, r.stderr

    sources = [json.loads(l) for l in (s / "sources" / "sources.jsonl").read_text().splitlines()]
    assert len(sources) == 3  # URL dedup: a.example.com/x 는 1건
    assert sources[0]["id"] == "src_001" and sources[0]["observed_at"]

    claims = [json.loads(l) for l in (s / "artifacts" / "claim_ledger.jsonl").read_text().splitlines()]
    assert claims[0]["source_ids"] == ["src_001", "src_002"]  # URL→id 매핑

    qlog = (s / "artifacts" / "query_log.md").read_text()
    assert "DUP of" in qlog  # 공백/대소문자 정규화 후 교차 에이전트 중복 검출
    assert "WebSearch 호출 13건" in qlog  # 8 + 5 합산

    assert "리드1" in (s / "artifacts" / "expansion_log.md").read_text()


def test_merged_ledger_passes_gate(tmp_path):
    """취합 산출물이 validate_ledger.py에 무수정으로 물려 exit 0."""
    s = make_session(tmp_path, [RET_A, RET_B])
    (s / "outputs").mkdir()
    assert run_merge(s).returncode == 0
    r = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_ledger.py"), "--session", str(s)],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    verified = json.loads((s / "outputs" / "verified_claims.json").read_text())
    assert len(verified) == 1  # 독립 2도메인 + counter_search + primary → verified


def test_missing_input_exit2(tmp_path):
    (tmp_path / "artifacts").mkdir()
    r = run_merge(tmp_path)
    assert r.returncode == 2


def test_domain_grade_normalization(tmp_path):
    """같은 도메인에 에이전트별 상이 등급 → 최빈(동률 시 보수) 등급으로 통일, 게이트 통과."""
    a = dict(RET_A, sources=[
        {"url": "https://d.example.com/1", "title": "1", "domain": "d.example.com", "quality_rating": "A"},
        {"url": "https://b.example.org/y", "title": "B", "domain": "b.example.org", "quality_rating": "B"},
    ], claims=[dict(RET_A["claims"][0], source_urls=["https://d.example.com/1", "https://b.example.org/y"])])
    b = dict(RET_B, sources=[
        {"url": "https://d.example.com/2", "title": "2", "domain": "d.example.com", "quality_rating": "B"},
        {"url": "https://d.example.com/3", "title": "3", "domain": "d.example.com", "quality_rating": "B"},
    ])
    s = make_session(tmp_path, [a, b])
    (s / "outputs").mkdir()
    r = run_merge(s)
    assert r.returncode == 0
    assert "정규화" in r.stderr
    sources = [json.loads(l) for l in (s / "sources" / "sources.jsonl").read_text().splitlines()]
    d_grades = {x["quality_rating"] for x in sources if x["domain"] == "d.example.com"}
    assert d_grades == {"B"}  # 최빈 B(2표) > A(1표)
    gate = subprocess.run(
        [sys.executable, str(SCRIPTS / "validate_ledger.py"), "--session", str(s)],
        capture_output=True, text=True,
    )
    assert gate.returncode == 0, gate.stderr  # 등급 모순 하드에러 없음


def test_unknown_claim_url_warns(tmp_path):
    bad = dict(RET_A, claims=[{"text": "x", "risk": "normal", "claim_type": "descriptive",
                               "source_urls": ["https://nowhere.example.com/"]}])
    s = make_session(tmp_path, [bad])
    r = run_merge(s)
    assert r.returncode == 0
    assert "미등록 URL" in r.stderr


# ── evidence 승계 (v2.10.0) ──────────────────────────────────────────────

def _claim_with_evidence(evidence):
    return dict(RET_A["claims"][0], evidence=evidence)


def test_evidence_url_remapped_to_source_id(tmp_path):
    """에이전트는 전역 id를 모르므로 source_url로 쓰고, 취합기가 src_xxx로 바꾼다 (슬래시·대소문자 정규화 포함)."""
    a = dict(RET_A, claims=[_claim_with_evidence([
        {"source_url": "https://B.example.org/y/", "quote": "벤치마크에서 처리량이 30% 늘었다고 보고했다", "locator": "## Results"},
        {"source_url": "https://a.example.com/x", "quote": "Throughput increased by 30 percent in v2"},
    ])])
    s = make_session(tmp_path, [a, RET_B])
    r = run_merge(s)
    assert r.returncode == 0, r.stderr
    claims = [json.loads(l) for l in (s / "artifacts" / "claim_ledger.jsonl").read_text().splitlines()]
    ev = claims[0]["evidence"]
    assert [e["source_id"] for e in ev] == ["src_002", "src_001"]
    assert ev[0]["quote"].startswith("벤치마크") and ev[0]["locator"] == "## Results"
    assert "locator" not in ev[1]  # 선택 필드는 없으면 생략


def test_evidence_unknown_url_dropped_with_warning(tmp_path):
    a = dict(RET_A, claims=[_claim_with_evidence([
        {"source_url": "https://nowhere.example.com/", "quote": "레지스트리에 없는 출처의 구절은 버려야 한다"},
    ])])
    s = make_session(tmp_path, [a])
    r = run_merge(s)
    assert r.returncode == 0
    assert "evidence" in r.stderr and "미등록" in r.stderr
    claims = [json.loads(l) for l in (s / "artifacts" / "claim_ledger.jsonl").read_text().splitlines()]
    assert claims[0]["evidence"] == []


def test_no_evidence_field_stays_absent(tmp_path):
    """evidence를 안 쓴 반환(구 계약)은 ledger에도 evidence 키를 만들지 않는다 — 구 세션 호환."""
    s = make_session(tmp_path, [RET_A])
    assert run_merge(s).returncode == 0
    claims = [json.loads(l) for l in (s / "artifacts" / "claim_ledger.jsonl").read_text().splitlines()]
    assert "evidence" not in claims[0]
