#!/usr/bin/env python3
"""레퍼런스 이미지 수집기 — 후보 페이지 URL에서 큰 이미지만 내려받아 목록을 남긴다.

리서치(주장 검증·보고서)가 아니라 "참고용 이미지 모으기"만 한다. 페이지 HTML은 insane-search
엔진으로 받는다(차단 우회는 그쪽 정본). 엔진이 없으면 단순 요청(curl, 없으면 urllib)만 하고, 막힌
페이지는 blocked로 기록한다 — 우회 기법을 여기에 다시 구현하지 않는다.

입력: URL 인자 또는 --urls-file(한 줄에 `URL<TAB>선정 이유`).
출력(--out): images/pNN/MM.ext, manifest.json, candidates.md
엔진 위치: --engine-dir > $INSANE_SEARCH_ENGINE_DIR > 플러그인 캐시 최신 버전 탐색.
표준 라이브러리만 쓴다.
"""

import argparse
import glob
import hashlib
import html
import ipaddress
import json
import os
import re
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request
from datetime import datetime, timezone

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_HTML_BYTES = 8 * 1024 * 1024
IMG_EXT = (".jpg", ".jpeg", ".png", ".webp", ".gif")
LAZY_ATTRS = ("src", "data-src", "data-original", "data-lazy-src", "data-lazy", "data-url", "data-img")
SRCSET_ATTRS = ("srcset", "data-srcset")


# ── 엔진 ─────────────────────────────────────────────────────────────

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


# ── 안전 ─────────────────────────────────────────────────────────────

def is_safe_url(url):
    """http(s)이고 사설·루프백 주소로 풀리지 않는 URL만 허용한다."""
    try:
        p = urllib.parse.urlsplit(url)
    except ValueError:
        return False
    if p.scheme not in ("http", "https") or not p.hostname:
        return False
    try:
        infos = socket.getaddrinfo(p.hostname, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(str(info[4][0]).split("%")[0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            return False
    return True


# ── 페이지 받기 ──────────────────────────────────────────────────────

def _ssl_context():
    # python.org 배포본은 CA 저장소가 비어 있을 수 있다 — certifi가 있으면 쓴다.
    try:
        import certifi  # type: ignore
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def _curl_get(url, referer, limit, timeout):
    """시스템 인증서를 쓰는 curl로 받는다. (data, final_url) — 실패면 예외."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        path = tmp.name
    try:
        cmd = ["curl", "-sSL", "--compressed", "--max-time", str(timeout), "--max-filesize", str(limit),
               "-A", UA, "-H", "Accept-Language: ko-KR,ko;q=0.9,en;q=0.8",
               "-o", path, "-w", "%{http_code} %{url_effective}"]
        if referer:
            cmd += ["-e", referer]
        r = subprocess.run(cmd + [url], capture_output=True, text=True, timeout=timeout + 5)
        code, _, final = r.stdout.strip().partition(" ")
        if r.returncode != 0 or not code.startswith("2"):
            raise OSError(f"curl rc={r.returncode} http={code}")
        with open(path, "rb") as f:
            return f.read(limit + 1), final or url
    finally:
        os.unlink(path)


def _http_get(url, referer=None, limit=MAX_HTML_BYTES, timeout=20):
    """(data, final_url, charset). curl 우선, 없으면 urllib."""
    if shutil.which("curl"):
        data, final = _curl_get(url, referer, limit, timeout)
        charset = "utf-8"
    else:
        headers = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8"}
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
            data, final, charset = r.read(limit + 1), r.geturl(), r.headers.get_content_charset() or "utf-8"
    if len(data) > limit:
        raise ValueError("too_large")
    return data, final, charset


def fetch_html(url, fetch, timeout, no_playwright):
    """(html, final_url, via) 또는 (None, url, 사유)."""
    if fetch is not None:
        try:
            res = fetch(url, timeout=timeout, max_attempts=8, enable_playwright=not no_playwright,
                        enable_extraction=False, enable_markdown=False)
            if getattr(res, "ok", False) and getattr(res, "content", ""):
                return res.content, getattr(res, "final_url", "") or url, "insane-search"
            return None, url, f"blocked:{getattr(res, 'stop_reason', '') or 'engine'}"
        except Exception as e:
            return None, url, f"blocked:engine_error:{type(e).__name__}"
    try:
        data, final, cs = _http_get(url, timeout=timeout)
        return data.decode(cs, errors="replace"), final, "direct"
    except Exception as e:
        return None, url, f"blocked:{type(e).__name__}"


# ── 이미지 후보 뽑기 ─────────────────────────────────────────────────

TAG_RE = re.compile(r"<(img|source|meta)\b([^>]*)>", re.I)
ATTR_RE = re.compile(r'([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("([^"]*)"|\'([^\']*)\'|([^\s>]+))')
RAW_IMG_RE = re.compile(r'https?:(?:\\?/){2}[^"\'\s<>()]+?\.(?:jpe?g|png|webp|gif)(?:\?[^"\'\s<>()]*)?', re.I)
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.I | re.S)


def _attrs(s):
    out = {}
    for m in ATTR_RE.finditer(s):
        out[m.group(1).lower()] = html.unescape(m.group(3) or m.group(4) or m.group(5) or "")
    return out


def _largest_from_srcset(v):
    best, best_w = None, -1
    for part in v.split(","):
        bits = part.strip().split()
        if not bits:
            continue
        w = 0
        if len(bits) > 1 and bits[1][:-1].replace(".", "").isdigit():
            w = float(bits[1][:-1])
        if w >= best_w:
            best, best_w = bits[0], w
    return best


def extract_title(page):
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', page, re.I)
    if m:
        t = m.group(1)
    else:
        tm = TITLE_RE.search(page)
        t = tm.group(1) if tm else ""
    t = re.sub(r"\s+", " ", html.unescape(t)).strip()
    return t[:80]


def extract_image_urls(page, base):
    seen, out = set(), []

    def add(u):
        if not u or u.startswith("data:") or any(ch in u for ch in "{}$"):  # 템플릿 자리표시자
            return
        u = urllib.parse.urljoin(base, u.replace("\\/", "/").strip())
        u = urllib.parse.quote(u, safe=":/?#[]@!&'()*+,;=%~")  # 한글 경로
        path = urllib.parse.urlsplit(u).path.lower()
        if path.endswith(".svg") or path.endswith(".ico"):
            return
        if u not in seen:
            seen.add(u)
            out.append(u)

    for m in TAG_RE.finditer(page):
        tag, a = m.group(1).lower(), _attrs(m.group(2))
        if tag == "meta":
            if a.get("property", a.get("name", "")).lower() in ("og:image", "twitter:image"):
                add(a.get("content"))
            continue
        for k in LAZY_ATTRS:
            if a.get(k):
                add(a[k])
        for k in SRCSET_ATTRS:
            if a.get(k):
                add(_largest_from_srcset(a[k]))
    # 스크립트 JSON 안에만 있는 상세 이미지(SPA)
    for m in RAW_IMG_RE.finditer(page):
        add(m.group(0))
    return out


# ── 이미지 크기 (헤더만 해석) ────────────────────────────────────────

def image_size(b):
    """(kind, w, h) — 모르면 (None, 0, 0)."""
    if b[:8] == b"\x89PNG\r\n\x1a\n" and len(b) >= 24:
        w, h = struct.unpack(">II", b[16:24])
        return "png", w, h
    if b[:6] in (b"GIF87a", b"GIF89a"):
        w, h = struct.unpack("<HH", b[6:10])
        return "gif", w, h
    if b[:4] == b"RIFF" and b[8:12] == b"WEBP":
        chunk = b[12:16]
        if chunk == b"VP8 " and len(b) >= 30:
            w, h = struct.unpack("<HH", b[26:30])
            return "webp", w & 0x3FFF, h & 0x3FFF
        if chunk == b"VP8L" and len(b) >= 25:
            bits = int.from_bytes(b[21:25], "little")
            return "webp", (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
        if chunk == b"VP8X" and len(b) >= 30:
            return "webp", int.from_bytes(b[24:27], "little") + 1, int.from_bytes(b[27:30], "little") + 1
    if b[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(b):
            if b[i] != 0xFF:
                i += 1
                continue
            marker = b[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            seg = struct.unpack(">H", b[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", b[i + 5:i + 9])
                return "jpg", w, h
            i += 2 + seg
    return None, 0, 0


# ── 수집 ─────────────────────────────────────────────────────────────

def collect_page(idx, url, note, out_dir, fetch, opts, downloader):
    rec = {"n": idx, "url": url, "note": note, "domain": urllib.parse.urlsplit(url).hostname or "",
           "title": "", "via": "", "status": "", "found": 0, "images": []}
    if not is_safe_url(url):
        rec["status"] = "skipped:unsafe_url"
        return rec
    page, final, via = fetch_html(url, fetch, opts.timeout, opts.no_playwright)
    rec["via"] = via
    if page is None:
        rec["status"] = via
        return rec
    rec["title"] = extract_title(page)
    cands = extract_image_urls(page, final)
    rec["found"] = len(cands)
    pdir = os.path.join(out_dir, "images", f"p{idx:02d}")
    tried = 0
    for src in cands:
        if len(rec["images"]) >= opts.max_per_page or tried >= opts.max_tries:
            break
        tried += 1
        if not is_safe_url(src):
            continue
        try:
            data = downloader(src, final)
        except Exception:
            continue
        kind, w, h = image_size(data[:65536])
        if not kind or not (w >= opts.min_width or h >= opts.min_long):
            continue
        os.makedirs(pdir, exist_ok=True)
        name = f"{len(rec['images']) + 1:02d}.{kind}"
        path = os.path.join(pdir, name)
        with open(path, "wb") as f:
            f.write(data)
        rec["images"].append({"src": src, "file": os.path.relpath(path, out_dir), "w": w, "h": h,
                              "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
    rec["status"] = "ok" if rec["images"] else "no_large_images"
    return rec


def default_downloader(src, referer):
    data, _, _ = _http_get(src, referer=referer, limit=MAX_IMAGE_BYTES)
    return data


def write_candidates(out_dir, topic, pages):
    def cell(s):
        return str(s).replace("|", "/").replace("\n", " ")

    lines = [f"# 레퍼런스 후보 — {cell(topic)}", "",
             f"수집: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} · "
             "참고용 수집본이다. 이미지는 각 판매처의 저작물이므로 재사용·생성 입력으로 쓰지 않는다.", "",
             "| # | 도메인 | 제목 | 이미지 | 가장 긴 이미지 | 상태 | 선정 이유 | URL |",
             "|---|---|---|---|---|---|---|---|"]
    for p in pages:
        longest = max(p["images"], key=lambda i: i["h"], default=None)
        lon = f"{longest['w']}×{longest['h']} `{longest['file']}`" if longest else "-"
        lines.append(f"| {p['n']} | {cell(p['domain'])} | {cell(p['title']) or '-'} | {len(p['images'])} | "
                     f"{lon} | {cell(p['status'])} | {cell(p['note']) or '-'} | {p['url']} |")
    lines += ["", "상태: `ok` 수집됨 · `no_large_images` 페이지는 열렸지만 큰 이미지가 HTML에 없음"
              "(JS 렌더 필요 가능) · `blocked:*` 페이지를 못 엶 · `skipped:unsafe_url` 허용 안 되는 주소", ""]
    with open(os.path.join(out_dir, "candidates.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def read_targets(args):
    targets = [(u, "") for u in args.urls]
    if args.urls_file:
        with open(args.urls_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                url, _, note = line.partition("\t")
                targets.append((url.strip(), note.strip()))
    dedup, seen = [], set()
    for u, n in targets:
        if u not in seen:
            seen.add(u)
            dedup.append((u, n))
    return dedup


def main(argv=None, downloader=default_downloader, fetch=None):
    p = argparse.ArgumentParser(description="후보 페이지에서 레퍼런스 이미지만 수집한다")
    p.add_argument("urls", nargs="*", help="후보 페이지 URL")
    p.add_argument("--urls-file", help="한 줄에 `URL<TAB>선정 이유`")
    p.add_argument("--out", required=True, help="출력 폴더")
    p.add_argument("--topic", default="", help="candidates.md 제목에 쓸 주제")
    p.add_argument("--min-width", type=int, default=500, help="이 폭 이상만 저장 (기본 500)")
    p.add_argument("--min-long", type=int, default=1500, help="폭이 작아도 이 높이 이상이면 저장 (기본 1500)")
    p.add_argument("--max-per-page", type=int, default=20)
    p.add_argument("--max-tries", type=int, default=60, help="페이지당 다운로드 시도 상한")
    p.add_argument("--timeout", type=int, default=20)
    p.add_argument("--no-playwright", action="store_true", help="엔진의 브라우저 폴백을 끈다(더 빠름)")
    p.add_argument("--engine-dir", help="insane-search 스킬 디렉터리 (engine/ 패키지를 담은 곳)")
    args = p.parse_args(argv)

    targets = read_targets(args)
    if not targets:
        print("URL이 없다 — 인자나 --urls-file로 넘긴다", file=sys.stderr)
        return 2
    if fetch is None:
        fetch = _load_fetch(_find_engine_dir(args.engine_dir))
        if fetch is None:
            print("insane-search 엔진 없음 — 단순 요청만 한다(막힌 페이지는 blocked)", file=sys.stderr)
    os.makedirs(args.out, exist_ok=True)

    pages = [collect_page(i, u, n, args.out, fetch, args, downloader) for i, (u, n) in enumerate(targets, 1)]
    manifest = {"topic": args.topic, "collected_at": datetime.now(timezone.utc).isoformat(),
                "engine": "insane-search" if fetch is not None else "direct",
                "min_width": args.min_width, "min_long": args.min_long, "pages": pages}
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    write_candidates(args.out, args.topic, pages)

    ok = sum(1 for x in pages if x["status"] == "ok")
    total = sum(len(x["images"]) for x in pages)
    print(json.dumps({"pages": len(pages), "pages_ok": ok, "images": total,
                      "candidates": os.path.join(args.out, "candidates.md")}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
