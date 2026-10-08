"""v2.10.0 원문 인용 게이트(7a~7e) 테스트.

fixture의 스냅샷 문장은 2026-10-08 실측에서 실제 출처 페이지로 확인한 문장이다.
지난 리서치(Workspace_Builder arch_ai_render_workspace_20260911_1735)에서 verified로
통과했던 고위험 주장 8건을 재현한다 — 일치 4건은 verified 유지, 불일치 4건은 unresolved.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills" / "insane-research-main" / "scripts"

COUNTER = {"query": "반증 검색", "urls": [], "summary": "반증 없음"}

# (claim_id, 주장, 에이전트가 낸 구절, 스냅샷 원문, 기대 status)
CASES = [
    ("clm_024", "FLUX ControlNet Union Pro는 7개 모드만 지원하고 lineart가 없다",
     "canny (0), tile (1), depth (2), blur (3), pose (4), gray (5), low quality (6)",
     "Supported control modes: canny (0), tile (1), depth (2), blur (3), pose (4), gray (5), low quality (6).",
     "verified"),
    ("clm_061", "SketchUp 2026.2에서 Sketchup.load/require가 LoadError를 raise한다",
     "Made Sketchup.load and Sketchup.require raise a `LoadError` when the file cannot be found",
     "## SketchUp 2026.2\n### Ruby API Bug Fixes\n* Made Sketchup.load and Sketchup.require raise a `LoadError` when the file cannot be found, matching Ruby.",
     "verified"),
    ("clm_002", "View#write_image 지원 포맷은 png/jpg/jpeg/gif/bmp/tif",
     "Supported file types are .png, .jpg, .jpeg, gif, .bmp, .tif.",
     "Supported file types are `.png`, `.jpg`, `.jpeg`, `gif`, `.bmp`, `.tif`. For other file formats use Model#export.",
     "verified"),
    ("clm_005", "OpenRouter 이미지 API 응답 usage에 정확한 USD 비용이 들어 있다",
     "the usage object in every response includes the exact cost in USD.",
     "Pricing is transparent: the `usage` object in every response includes the exact cost in USD.",
     "verified"),
    ("clm_014", "IP-Adapter Plus는 COCO2017에서 CLIP-I 0.828 / CLIP-T 0.588을 기록했다",
     "IP-Adapter Plus achieves CLIP-I 0.828 and CLIP-T 0.588 on COCO2017",
     "IP-Adapter steers a pretrained diffusion model with a reference image while you keep a text prompt. "
     "ip-adapter-plus_sdxl_vit-h uses patch embeddings and a ViT-H image encoder.",
     "unresolved"),
    ("clm_029", "Real-ESRGAN은 순수 합성 데이터로 학습한 GAN 업스케일러다",
     "Real-ESRGAN is trained purely on synthetic data to model real degradations",
     "Real-ESRGAN is an open-source image upscaling model from Tencent ARC Lab (2021). "
     "It is trained on degraded real-world images with sensor noise and JPEG compression.",
     "unresolved"),
    ("clm_046", "Stability /v2beta/stable-image/edit/inpaint는 mode=mask와 mode=search를 지원한다",
     "POST /v2beta/stable-image/edit/inpaint supports mode=mask and mode=search",
     "Endpoint: /v2alpha/generation/stable-image/inpaint. To search and replace, set the `mode` parameter "
     "to `search` and provide a short description in `search_prompt`.",
     "unresolved"),
    ("clm_013", "Midjourney 스타일 코드는 분해할 수 없는 블랙박스다",
     "style codes are a black box that cannot be decomposed into components",
     "A style reference code is a number that points at a style in Midjourney's internal style library. "
     "Midjourney publishes no format specification for style codes.",
     "unresolved"),
]


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_session(tmp_path, claims_spec, schema: "int | None" = 2):
    """claims_spec: list of (claim_dict_overrides, snapshot_text_for_primary, snapshot_status)."""
    (tmp_path / "artifacts").mkdir()
    (tmp_path / "sources" / "snapshots").mkdir(parents=True)
    (tmp_path / "outputs").mkdir()
    state = {"session_id": "t", "progress": {}}
    if schema is not None:
        state["ledger_schema"] = schema
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")

    sources, claims = [], []
    for n, (claim, snap_text, snap_status) in enumerate(claims_spec, 1):
        a, b = f"src_{2*n-1:03d}", f"src_{2*n:03d}"
        snap_rel = f"sources/snapshots/{a}.txt"
        snap = {"path": snap_rel, "status": snap_status, "chars": len(snap_text or ""),
                "fetched_at": "2026-10-08T00:00:00Z", "via": "test"}
        if snap_status == "ok":
            (tmp_path / snap_rel).write_text(snap_text, encoding="utf-8")
            snap["sha256"] = _sha(snap_text)
        sources.append({"id": a, "url": f"https://docs.org{n}.example.com/p", "domain": f"docs.org{n}.example.com",
                        "type": "official_docs", "quality_rating": "A", "snapshot": snap})
        sources.append({"id": b, "url": f"https://bench.other{n}.example.net/q", "domain": f"bench.other{n}.example.net",
                        "type": "independent_benchmark", "quality_rating": "B"})
        rec = {"claim_id": f"clm_{n:03d}", "text": "주장", "risk": "high", "claim_type": "descriptive",
               "source_ids": [a, b], "counter_search": COUNTER, "valid_at": "2026-10-01"}
        rec.update(claim)
        # evidence 기본 대상은 1차 출처(a)
        for e in rec.get("evidence") or []:
            e.setdefault("source_id", a)
        claims.append(rec)

    (tmp_path / "sources" / "sources.jsonl").write_text(
        "\n".join(json.dumps(s, ensure_ascii=False) for s in sources) + "\n", encoding="utf-8")
    (tmp_path / "artifacts" / "claim_ledger.jsonl").write_text(
        "\n".join(json.dumps(c, ensure_ascii=False) for c in claims) + "\n", encoding="utf-8")
    return tmp_path


def run_gate(session):
    r = subprocess.run([sys.executable, str(SCRIPTS / "validate_ledger.py"), "--session", str(session)],
                       capture_output=True, text=True)
    out = session / "outputs"
    def load(name):
        p = out / name
        return json.loads(p.read_text()) if p.exists() else []
    statuses = {c["claim_id"]: c for c in load("verified_claims.json") + load("unresolved_claims.json") + load("refuted_claims.json")}
    return r, statuses


def _status(statuses, n):
    return statuses[f"clm_{n:03d}"]["status"]


# ── 지난 표본 8건 재현 ───────────────────────────────────────────────────

def test_past_sample_eight_claims(tmp_path):
    spec = [({"text": text, "evidence": [{"quote": quote}]}, snap, "ok") for _cid, text, quote, snap, _exp in CASES]
    s = build_session(tmp_path, spec)
    r, st = run_gate(s)
    assert r.returncode == 0, r.stderr
    got = [_status(st, i + 1) for i in range(len(CASES))]
    assert got == [exp for *_x, exp in CASES], got
    bad = st["clm_005"]  # clm_014 재현 (5번째)
    assert bad["evidence_check"]["passed"] == 0 and bad["evidence_check"]["failed"] == 1
    assert "원문에 없음" in bad["status_reason"]


def test_same_sample_old_schema_is_exempt(tmp_path):
    """ledger_schema가 없는 기존 세션은 이전 규칙 — 불일치 4건도 verified (호환)."""
    spec = [({"text": text, "evidence": [{"quote": quote}]}, snap, "ok") for _cid, text, quote, snap, _exp in CASES]
    s = build_session(tmp_path, spec, schema=None)
    r, st = run_gate(s)
    assert r.returncode == 0, r.stderr
    assert all(_status(st, i + 1) == "verified" for i in range(len(CASES)))


# ── 7a~7e 개별 규칙 ──────────────────────────────────────────────────────

SNAP = "The new release raised the default timeout from 30 seconds to 90 seconds for all regions."
GOOD_Q = "raised the default timeout from 30 seconds to 90 seconds"


def test_7a_high_risk_without_evidence(tmp_path):
    s = build_session(tmp_path, [({}, SNAP, "ok")])
    r, st = run_gate(s)
    assert r.returncode == 0, r.stderr
    assert _status(st, 1) == "unresolved"
    assert "evidence 없음" in st["clm_001"]["status_reason"]


def test_7b_evidence_source_not_in_claim_is_hard_error(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": GOOD_Q, "source_id": "src_999"}]}, SNAP, "ok")])
    r, _ = run_gate(s)
    assert r.returncode == 2
    assert "evidence" in r.stderr


def test_7c_blocked_snapshot_only(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": GOOD_Q}]}, None, "blocked")])
    r, st = run_gate(s)
    assert r.returncode == 0, r.stderr
    assert _status(st, 1) == "unresolved"
    assert "스냅샷" in st["clm_001"]["status_reason"]


def test_7d_fabricated_quote(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": "raised the default timeout from 30 seconds to 120 seconds"}]}, SNAP, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "unresolved"


def test_7e_one_passing_evidence_is_enough(tmp_path):
    s = build_session(tmp_path, [({"evidence": [
        {"quote": "a completely invented sentence that is not on the page"},
        {"quote": GOOD_Q, "locator": "## Changes"},
    ]}, SNAP, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "verified"
    assert st["clm_001"]["evidence_check"] == {"passed": 1, "failed": 1, "reasons": st["clm_001"]["evidence_check"]["reasons"]}


def test_normalization_whitespace_quotes_case_markdown(tmp_path):
    snap = "## Notes\nThe **new release** raised the “default  timeout”\nfrom 30 seconds to 90 seconds."
    q = 'the new release RAISED the "default timeout" from 30 seconds to 90 seconds'
    s = build_session(tmp_path, [({"evidence": [{"quote": q}]}, snap, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "verified"


def test_no_fuzzy_match_for_near_miss(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": "raised the default timeout from 30 second to 90 seconds"}]}, SNAP, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "unresolved"


def test_quote_length_bounds(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": "90 seconds"}]}, SNAP, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "unresolved"
    assert any("길이" in x for x in st["clm_001"]["evidence_check"]["reasons"])


def test_snapshot_tampered_hash_mismatch(tmp_path):
    s = build_session(tmp_path, [({"evidence": [{"quote": GOOD_Q}]}, SNAP, "ok")])
    (s / "sources" / "snapshots" / "src_001.txt").write_text(SNAP + " edited", encoding="utf-8")
    _, st = run_gate(s)
    assert _status(st, 1) == "unresolved"
    assert any("sha256" in x for x in st["clm_001"]["evidence_check"]["reasons"])


def test_normal_risk_claim_not_required(tmp_path):
    s = build_session(tmp_path, [({"risk": "normal"}, SNAP, "ok")])
    _, st = run_gate(s)
    assert _status(st, 1) == "verified"
