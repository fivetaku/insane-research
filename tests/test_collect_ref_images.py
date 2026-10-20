"""collect_ref_images.py 테스트 — 가짜 엔진·다운로더를 주입해 네트워크 없이 검증한다."""

import importlib.util
import json
import struct
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parent.parent / "skills" / "insane-research-refs" / "scripts"
          / "collect_ref_images.py")
spec = importlib.util.spec_from_file_location("collect_ref_images", SCRIPT)
assert spec and spec.loader
cri = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cri)


def png(w, h):
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", w, h) + b"\x08\x02\x00\x00\x00" + b"\x00" * 64


def jpg(w, h):
    return (b"\xff\xd8" + b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
            + b"\xff\xc0" + struct.pack(">HBHH", 17, 8, h, w) + b"\x00" * 64)


PAGE_A = """<html><head><title>선크림 50ml | 상점</title>
<meta property="og:image" content="https://cdn.a.com/og.png"></head><body>
<img src="/img/icon.png"><img data-src="https://cdn.a.com/detail-1.jpg">
<img srcset="https://cdn.a.com/s-300.png 300w, https://cdn.a.com/s-1200.png 1200w">
<img src="data:image/gif;base64,AAAA"><img src="/logo.svg">
<script>window.__D={"detail":"https:\\/\\/cdn.a.com\\/long.jpg"}</script>
</body></html>"""

IMAGES = {
    "https://cdn.a.com/og.png": png(1200, 630),
    "https://a.com/img/icon.png": png(48, 48),
    "https://cdn.a.com/detail-1.jpg": jpg(1000, 18000),
    "https://cdn.a.com/s-1200.png": png(1200, 800),
    "https://cdn.a.com/long.jpg": jpg(400, 9000),
}


class R:
    def __init__(self, ok, content="", final_url="", stop_reason=""):
        self.ok, self.content, self.final_url, self.stop_reason = ok, content, final_url, stop_reason


def fake_fetch(url, **kw):
    assert kw["enable_markdown"] is False and kw["enable_extraction"] is False
    if url == "https://a.com/p/1":
        return R(True, PAGE_A, url)
    if url == "https://b.com/p/2":
        return R(True, "<html><title>빈 페이지</title><img src='/x.png'></html>", url)
    return R(False, stop_reason="waf_block")


def fake_download(src, referer):
    if src not in IMAGES:
        raise OSError("404")
    return IMAGES[src]


def run(tmp_path, monkeypatch, urls, extra=()):
    monkeypatch.setattr(cri, "is_safe_url", lambda u: "evil" not in u)
    out = tmp_path / "out"
    targets = tmp_path / "targets.tsv"
    targets.write_text("\n".join(urls) + "\n", encoding="utf-8")
    code = cri.main(["--urls-file", str(targets), "--out", str(out), "--topic", "선크림", *extra],
                    downloader=fake_download, fetch=fake_fetch)
    return code, out, json.loads((out / "manifest.json").read_text(encoding="utf-8"))


def test_collects_only_large_images_and_skips_icons(tmp_path, monkeypatch):
    code, out, m = run(tmp_path, monkeypatch, ["https://a.com/p/1\t사용자 제공"])
    assert code == 0
    page = m["pages"][0]
    assert page["status"] == "ok" and page["via"] == "insane-search"
    assert page["title"] == "선크림 50ml | 상점"
    srcs = [i["src"] for i in page["images"]]
    # 아이콘(48px)·data URI·svg 제외, srcset은 가장 큰 후보, 스크립트 JSON 속 긴 이미지 포함
    assert "https://a.com/img/icon.png" not in srcs
    assert "https://cdn.a.com/s-1200.png" in srcs and "https://cdn.a.com/s-300.png" not in srcs
    assert "https://cdn.a.com/long.jpg" in srcs  # 폭 400이어도 높이 9000이라 저장
    detail = next(i for i in page["images"] if i["src"].endswith("detail-1.jpg"))
    assert (detail["w"], detail["h"]) == (1000, 18000)
    assert (out / detail["file"]).read_bytes() == IMAGES["https://cdn.a.com/detail-1.jpg"]
    assert len(detail["sha256"]) == 64


def test_candidates_table_marks_each_status(tmp_path, monkeypatch):
    code, out, m = run(tmp_path, monkeypatch, [
        "https://a.com/p/1\t사용자 제공", "https://b.com/p/2\t자사몰", "https://c.com/p/3",
        "http://evil.local/x"])
    assert code == 0
    status = {p["url"]: p["status"] for p in m["pages"]}
    assert status["https://b.com/p/2"] == "no_large_images"
    assert status["https://c.com/p/3"].startswith("blocked:")
    assert status["http://evil.local/x"] == "skipped:unsafe_url"
    md = (out / "candidates.md").read_text(encoding="utf-8")
    assert "선크림 50ml / 상점" in md  # 표 칸을 깨는 | 는 치환
    assert "1000×18000" in md and "사용자 제공" in md and "재사용" in md


def test_exit_1_when_nothing_collected(tmp_path, monkeypatch):
    code, _, m = run(tmp_path, monkeypatch, ["https://c.com/p/3"])
    assert code == 1 and m["pages"][0]["status"].startswith("blocked:")


def test_max_per_page(tmp_path, monkeypatch):
    _, _, m = run(tmp_path, monkeypatch, ["https://a.com/p/1"], ["--max-per-page", "2"])
    assert len(m["pages"][0]["images"]) == 2


def test_image_size_webp_and_unknown():
    vp8x = b"RIFF" + b"\x00" * 4 + b"WEBPVP8X" + b"\x00" * 8 + (999).to_bytes(3, "little") + (1499).to_bytes(3, "little")
    assert cri.image_size(vp8x) == ("webp", 1000, 1500)
    assert cri.image_size(b"not an image") == (None, 0, 0)


def test_unsafe_urls_rejected():
    assert not cri.is_safe_url("file:///etc/passwd")
    assert not cri.is_safe_url("http://127.0.0.1/x")
    assert not cri.is_safe_url("http://10.0.0.5/x")


def test_skips_template_placeholders_and_quotes_korean_path():
    page = '<img src="/{$image_tiny}"><img src="/이미지/상세.jpg"><img src="https://x.com/a.png">'
    urls = cri.extract_image_urls(page, "https://shop.kr/p/1")
    assert not any("{" in u or "$" in u for u in urls)
    assert "https://shop.kr/%EC%9D%B4%EB%AF%B8%EC%A7%80/%EC%83%81%EC%84%B8.jpg" in urls
    assert "https://x.com/a.png" in urls
