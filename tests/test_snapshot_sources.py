"""snapshot_sources.py 테스트 — 가짜 insane-search 엔진을 주입해 네트워크 없이 검증한다."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "insane-research-main" / "scripts"

FAKE_ENGINE = '''
from dataclasses import dataclass

PAGES = {
    "https://docs.example.com/a": "The default timeout is 90 seconds in every region.",
    "https://big.example.com/b": "x" * 3_000_000,
}

@dataclass
class R:
    ok: bool
    content: str = ""
    final_url: str = ""
    verdict: str = ""
    extraction_source: str = ""

CALLS = []

def fetch(url, **kw):
    with open(__file__ + ".calls", "a") as f:
        f.write(url + "\\n")
    if url in PAGES:
        return R(ok=True, content=PAGES[url], final_url=url, verdict="strong_ok", extraction_source="raw")
    return R(ok=False, verdict="challenge")
'''


def make(tmp_path, claims, sources):
    eng = tmp_path / "fake_engine_root"
    (eng / "engine").mkdir(parents=True)
    (eng / "engine" / "__init__.py").write_text(FAKE_ENGINE, encoding="utf-8")
    s = tmp_path / "session"
    (s / "artifacts").mkdir(parents=True)
    (s / "sources").mkdir()
    (s / "sources" / "sources.jsonl").write_text("\n".join(json.dumps(x) for x in sources) + "\n")
    (s / "artifacts" / "claim_ledger.jsonl").write_text("\n".join(json.dumps(x) for x in claims) + "\n")
    return s, eng


def run(s, eng):
    return subprocess.run([sys.executable, str(SCRIPTS / "snapshot_sources.py"), "--session", str(s),
                           "--engine-dir", str(eng)], capture_output=True, text=True)


SOURCES = [
    {"id": "src_001", "url": "https://docs.example.com/a"},
    {"id": "src_002", "url": "https://blocked.example.com/x"},
    {"id": "src_003", "url": "https://normal-only.example.com/n"},
    {"id": "src_004", "url": "https://big.example.com/b"},
]
CLAIMS = [
    {"claim_id": "clm_001", "risk": "high", "source_ids": ["src_001", "src_002"]},
    {"claim_id": "clm_002", "risk": "normal", "source_ids": ["src_003"]},
    {"claim_id": "clm_003", "risk": "high", "source_ids": ["src_004"]},
]


def load_sources(s):
    return {x["id"]: x for x in map(json.loads, (s / "sources" / "sources.jsonl").read_text().splitlines())}


def test_snapshots_only_high_risk_sources(tmp_path):
    s, eng = make(tmp_path, CLAIMS, SOURCES)
    r = run(s, eng)
    assert r.returncode == 0, r.stderr
    calls = (eng / "engine" / "__init__.py.calls").read_text().split()
    assert "https://normal-only.example.com/n" not in calls  # normal 주장만 인용한 출처는 수집 안 함
    src = load_sources(s)
    ok = src["src_001"]["snapshot"]
    assert ok["status"] == "ok" and ok["path"] == "sources/snapshots/src_001.txt"
    body = (s / ok["path"]).read_bytes()
    assert ok["sha256"] == hashlib.sha256(body).hexdigest() and ok["chars"] == len(body.decode())
    assert ok["via"] == "raw" and ok["fetched_at"]
    assert src["src_002"]["snapshot"]["status"] == "blocked"
    assert src["src_004"]["snapshot"]["status"] == "too_large"
    assert not (s / "sources" / "snapshots" / "src_004.txt").exists()
    assert "snapshot" not in src["src_003"]


def test_rerun_skips_existing_ok_snapshot(tmp_path):
    s, eng = make(tmp_path, CLAIMS, SOURCES)
    assert run(s, eng).returncode == 0
    (eng / "engine" / "__init__.py.calls").unlink()
    assert run(s, eng).returncode == 0
    calls = (eng / "engine" / "__init__.py.calls").read_text().split()
    assert "https://docs.example.com/a" not in calls  # 이미 ok면 재수집 안 함 (해시 고정)


def test_snapshot_feeds_gate_end_to_end(tmp_path):
    """스냅샷 → validate_ledger 대조까지 실제로 물린다."""
    srcs = [
        {"id": "src_001", "url": "https://docs.example.com/a", "domain": "docs.example.com",
         "type": "official_docs", "quality_rating": "A"},
        {"id": "src_002", "url": "https://bench.other.net/b", "domain": "bench.other.net",
         "type": "independent_benchmark", "quality_rating": "B"},
    ]
    claims = [{"claim_id": "clm_001", "text": "기본 타임아웃은 90초", "risk": "high", "claim_type": "numeric",
               "source_ids": ["src_001", "src_002"],
               "counter_search": {"query": "q", "urls": [], "summary": "none"},
               "evidence": [{"source_id": "src_001", "quote": "The default timeout is 90 seconds"}]}]
    s, eng = make(tmp_path, claims, srcs)
    (s / "state.json").write_text('{"ledger_schema": 2}')
    (s / "outputs").mkdir()
    assert run(s, eng).returncode == 0
    g = subprocess.run([sys.executable, str(SCRIPTS / "validate_ledger.py"), "--session", str(s)],
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stderr
    verified = json.loads((s / "outputs" / "verified_claims.json").read_text())
    assert [c["claim_id"] for c in verified] == ["clm_001"]
    assert verified[0]["evidence_check"]["passed"] == 1


def test_missing_engine_exit2(tmp_path):
    s, _ = make(tmp_path, CLAIMS, SOURCES)
    r = subprocess.run([sys.executable, str(SCRIPTS / "snapshot_sources.py"), "--session", str(s),
                        "--engine-dir", str(tmp_path / "nope")], capture_output=True, text=True)
    assert r.returncode == 2
