# Adaptive Tool Strategy

리서치에 사용하는 도구 전략. 기본 도구(WebSearch, WebFetch, Bash/curl)만으로 충분한 리서치가 가능하며, MCP는 환경에 설치되어 있을 때 추가 활용한다.

---

## 기본 도구 (항상 가용)

### WebSearch — 검색

```python
# 범용 웹 검색
WebSearch(query="AI code assistants 2026 latest trends")

# 특정 사이트 한정 검색
WebSearch(query="site:x.com openclaw dreaming feature")
WebSearch(query="site:reddit.com ClaudeAI third-party harness")

# 학술 검색
WebSearch(query="transformer architecture survey 2025 arxiv")
```

모든 리서치의 시작점. 검색 결과(제목, snippet, URL)를 획득한다.

### WebFetch — 콘텐츠 추출

```python
WebFetch(url="https://example.com/article", prompt="Extract key findings and data")
```

검색에서 발견한 URL의 본문 추출. 대부분의 일반 웹페이지에서 동작.

**제한**: x.com(402), reddit.com(차단), 네이버 블로그(차단) 등 일부 사이트에서 실패 → 플랫폼별 접근 전략 또는 Fallback으로 전환.

### Bash(curl) — 직접 HTTP 요청

```bash
# 범용 웹페이지 읽기 (Jina Reader)
curl -s "https://r.jina.ai/https://example.com/article"

# RSS 피드 수집
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:5]:
    print(f'{e.title} — {e.link}')
"
```

WebFetch가 실패하는 사이트 우회, API 직접 호출, 플랫폼별 전략 실행에 사용.

### 사용 순서

1. **WebSearch**로 검색하여 관련 URL 확보
2. **WebFetch**로 URL 본문 추출 시도
3. WebFetch 실패 시 → **Bash(curl)**로 우회 (Jina Reader, 플랫폼별 API, Fallback 순)

---

## 플랫폼별 접근 전략

각 플랫폼의 최적 접근법. 모두 **API 키 불필요, 인증 불필요**로 동작한다.

### X/Twitter

WebFetch는 402로 차단됨. 아래 방법을 사용.

**검색 (트윗 발견)**

```python
WebSearch(query="site:x.com {검색어}")
```

**타임라인 조회 — Syndication API (최적)**

인증 불필요. 특정 핸들의 최근 ~20개 트윗 + engagement 수치(likes, RTs) 제공.

```bash
curl -sL "https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}" | \
python3 -c "
import sys, json, re, html
content = sys.stdin.read()
match = re.search(r'__NEXT_DATA__.*?>(.*?)</script>', content)
if match:
    data = json.loads(match.group(1))
    for e in data['props']['pageProps']['timeline']['entries']:
        if e['type'] == 'tweet':
            t = e['content']['tweet']
            print(f\"@{t['user']['screen_name']} ({t.get('created_at','?')})\")
            print(f\"  {html.unescape(t.get('full_text',''))[:300]}\")
            print(f\"  Likes: {t.get('favorite_count',0)} | RTs: {t.get('retweet_count',0)}\")
            print('---')
"
```

데이터: `full_text`, `screen_name`, `name`, `favorite_count`, `retweet_count`, `created_at`, `id_str`, `media_url_https`

제한: 최근 ~20개만, 비공개 계정 불가, 검색 불가(타임라인만). Syndication API는 비공식 엔드포인트 — X가 변경/차단 가능.

**개별 트윗 조회 — oEmbed API**

특정 트윗 URL을 알 때 전문 가져오기.

```bash
curl -sL "https://publish.twitter.com/oembed?url=https://x.com/{user}/status/{tweet_id}"
```

응답(JSON): `author_name`, `author_url`, `html`(트윗 전문 포함)

**조합 패턴 (검색 → 상세)**

```
1단계: WebSearch(query="site:x.com {키워드}") → 트윗 URL 획득
2단계: curl oEmbed API → 트윗 전문 획득
```

**실패하는 방법**: WebFetch(402), Nitter(종료됨), Wayback(SPA 미렌더링), RSS(X는 지원 중단)

---

### Reddit

WebFetch는 www/old 모두 차단됨. 아래 방법을 사용.

**JSON API — URL 뒤에 `.json`만 붙이면 된다 (최적)**

인증 불필요. **단, Mobile User-Agent 헤더 필수** (없으면 403/429).

```bash
# 서브레딧 핫 포스트
curl -sL \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15" \
  "https://www.reddit.com/r/{subreddit}/hot.json?limit=10"

# 서브레딧 검색
curl -sL \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15" \
  "https://www.reddit.com/r/{subreddit}/search.json?q={query}&restrict_sr=1"

# 개별 포스트 + 댓글
curl -sL \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15" \
  "https://www.reddit.com/r/{subreddit}/comments/{post_id}/{slug}/.json"
```

엔드포인트 패턴:
- `/r/{subreddit}/.json` — 포스트 목록
- `/r/{subreddit}/hot.json?limit=N` — 인기 포스트
- `/r/{subreddit}/new.json?limit=N` — 최신 포스트
- `/r/{subreddit}/top.json?t=week&limit=N` — 상위 포스트 (t: hour/day/week/month/year/all)
- `/r/{subreddit}/search.json?q={query}&restrict_sr=1` — 서브레딧 내 검색
- `/r/{subreddit}/comments/{post_id}/{slug}/.json` — 포스트 + 댓글

포스트 데이터: `title`, `author`, `score`, `selftext`(본문 마크다운), `url`, `num_comments`, `created_utc`, `link_flair_text`

댓글: 응답의 `[1]` 배열에 댓글 트리 — `author`, `body`, `score`, `replies`(재귀적)

**실패하는 방법**: WebFetch(차단), RSS(403, 2023년 이후 비인증 차단)

---

### YouTube

**자막 추출 — yt-dlp**

```bash
# 자막 다운로드 (영상 다운로드 없이)
yt-dlp --write-sub --write-auto-sub --sub-lang "zh-Hans,zh,en,ko" --skip-download -o "/tmp/%(id)s" "URL"

# 자막 파일 읽기
cat /tmp/VIDEO_ID.*.vtt
```

**영상 메타데이터**

```bash
yt-dlp --dump-json "URL"
```

**영상 검색**

```bash
yt-dlp --dump-json "ytsearch5:{검색어}"
```

주의: 자동 생성 자막은 행간 중복 가능 → 후처리 필요. yt-dlp가 설치되어 있지 않으면 `pip install yt-dlp`로 설치.

---

### GitHub

```bash
# 저장소 검색
gh search repos "{query}" --sort stars --limit 10

# 코드 검색
gh search code "{query}" --language python --limit 10

# 이슈 검색
gh search issues "{query}" --repo {owner}/{repo} --limit 10

# 저장소 README 읽기
gh api repos/{owner}/{repo}/readme --jq '.content' | base64 -d
```

공개 검색은 로그인 불필요. `gh auth login` 시 비공개 저장소 접근 가능.

---

### 범용 웹 — Jina Reader

WebFetch 실패 시 대체. 대부분의 일반 웹페이지를 마크다운으로 변환.

```bash
curl -s "https://r.jina.ai/https://example.com/article"
```

---

### RSS 피드

API 키 불필요. 블로그/뉴스 사이트의 최신 포스트 일괄 수집에 유용.

```bash
# 네이버 블로그 RSS
curl -sL "https://rss.blog.naver.com/{BLOG_ID}.xml"

# 티스토리 RSS
curl -sL "https://{blogname}.tistory.com/rss"

# 워드프레스 RSS
curl -sL "https://{domain}/feed"

# Python feedparser로 파싱
python3 -c "
import feedparser
for e in feedparser.parse('FEED_URL').entries[:10]:
    print(f'{e.title} — {e.link}')
    print(f'  {e.get(\"summary\",\"\")[:200]}')
    print('---')
"
```

---

## 접근 불가 시 우회 전략 (Fallback)

WebSearch/WebFetch/플랫폼별 전략 모두 실패했을 때 아래 순서로 우회 시도.

### 1. 모바일 URL 변환 + curl (UA 차단 우회)

도메인별 최적 방법:

| 도메인 패턴 | 최적 방법 |
|-----------|---------|
| `blog.naver.com` | 모바일 URL + iPhone UA |
| `*.tistory.com` | WebFetch (정상 작동) 또는 RSS |
| `brunch.co.kr` | WebFetch (정상 작동) |
| `linkedin.com` | WebSearch → WebFetch (정상 작동) |
| `*.naver.com` (기타) | Playwright MCP (JS 렌더링 필요) |
| 페이월 사이트 | Google 캐시 → Wayback → 대체 소스 |

```bash
# 네이버 블로그
curl -sL \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1" \
  -H "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8" \
  -H "Accept-Language: ko-KR,ko;q=0.9" \
  -H "Referer: https://m.naver.com/" \
  "https://m.blog.naver.com/PostView.naver?blogId={ID}&logNo={NO}"

# 일반 사이트
curl -sL \
  -H "User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15" \
  "{URL}"
```

### 2. OGP 메타태그 추출 (최소 제목+요약 확보)

```bash
curl -sL \
  -H "User-Agent: Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)" \
  "{URL}" \
  | grep -E '<meta property="og:|<meta name="description'
```

### 3. Google 캐시 / Wayback Machine

```bash
curl -sL "https://webcache.googleusercontent.com/search?q=cache:{URL}"
curl -sL "https://web.archive.org/web/{URL}"
```

### 4. curl_cffi (TLS 핑거프린트 차단 우회)

```python
# pip install curl_cffi 필요
from curl_cffi import requests
response = requests.get("{URL}", impersonate="chrome124")
print(response.text)
```

### 5. Playwright MCP (최후 수단)

JS 렌더링이 필수인 SPA 사이트에만 사용. MCP 부스터 섹션 참조.

### 응답 검증 규칙

curl 등으로 받은 응답이 실제 콘텐츠인지 아래 기준으로 판별한다:

| 판정 | 조건 | 조치 |
|------|------|------|
| **성공** | 본문 텍스트 1,000자 이상 + 주제 관련 키워드 포함 | 소스로 사용 |
| **부분 성공** | OG 메타태그나 제목+요약만 추출됨 | 보조 소스로 사용, `partial_content` 태그 |
| **실패 — 로그인 페이지** | `login`, `sign in`, `로그인`, `password` 키워드가 본문 상단에 집중 | 다음 Fallback 시도 |
| **실패 — CAPTCHA** | `captcha`, `verify`, `robot`, `보안 인증` 또는 본문 200자 미만 | 다음 Fallback 시도 |
| **실패 — 에러 페이지** | HTTP 4xx/5xx 또는 `404`, `not found`, `access denied` | 다음 Fallback 시도 |
| **실패 — 빈 SPA** | `<noscript>`, `<div id="root"></div>` 외 실질 콘텐츠 없음 | Playwright MCP 또는 포기 |

### Fallback 실행 규칙

1. **우회 성공 시**: 소스 신뢰도에 `via_fallback` 태그 추가, 어떤 방법으로 성공했는지 기록
2. **모든 우회 실패 시**: 실패 URL + 각 우회 방법별 시도 결과를 `sources/failed_urls.txt`에 기록
3. **대체 소스 재검색**: 동일 주제의 다른 소스를 WebSearch로 재검색

---

## MCP 부스터 (선택적)

환경에 설치되어 있으면 **우선 활용**한다. 없어도 기본 도구로 충분한 리서치가 가능하다.

> 해당 MCP 도구가 현재 환경에서 호출 가능할 때만 사용. 없으면 무시하고 기본 도구를 사용한다.

### Perplexity MCP

자체 크롤러로 네이버 블로그 포함 대부분의 차단 사이트 접근 가능.

```python
mcp__perplexity__perplexity_search(query="...")
mcp__perplexity__perplexity_research(query="...")
```

대체(MCP 없을 때): WebSearch + WebFetch, 또는 Jina Reader

### Firecrawl MCP

```python
firecrawl_search(query="...", limit=10)
firecrawl_scrape(url="...")
```

대체: WebSearch + Jina Reader

### Exa MCP

```python
mcp_websearch_web_search_exa(query="...", type="deep", numResults=10)
```

대체: WebSearch(여러 쿼리 변형으로 보완)

### Playwright MCP

JS 렌더링이 필수인 SPA 사이트 접근. 가장 느리지만 거의 모든 사이트 접근 가능.

```bash
# 설치: claude mcp add playwright npx @playwright/mcp@latest
```

대체: 해당 플랫폼의 API(Syndication API, JSON API 등) 사용

---

## 특수 도구 (선택적)

### GitHub MCP

```python
# MCP 사용 가능 시
mcp_grep_app_searchGitHub(query="...", language=["Python", "TypeScript"])

# 대체: gh CLI (항상 사용 가능)
# gh search repos "query" --sort stars --limit 10
```

### Context7 (라이브러리 문서)

```python
mcp_context7_resolve_library_id(libraryName="react", query="hooks")
mcp_context7_query_docs(libraryId="/facebook/react", query="useEffect")
```

대체: WebSearch로 공식 문서 검색 + WebFetch/Jina Reader로 추출

---

## Agents for Parallel Research (기본 = foreground 배치)

> ⚠️ **Rate-Limit & Reliability Guard** (SKILL.md): throttle to **2-3 concurrent** per batch, verify liveness after spawn (background agents can silently die with no notification → 무산출), and fall back to **main-thread sequential** when reliability matters. Do NOT launch a large `run_in_background=True` fan-out — it trips server-side rate-limits and the agents die.

**기본 예시 — foreground(blocking) 2-3개 배치** (안정 기본값. 경고와 일치):

```python
# 한 배치 = 2-3개. 이 배치가 끝난 뒤 다음 배치를 띄운다.
Task(
    subagent_type="Explore",
    description="Research subtopic A",
    prompt="Detailed research instructions...",
    mode="bypassPermissions",
)
Task(
    subagent_type="general-purpose",
    description="Research subtopic B",
    prompt="...",
    mode="bypassPermissions",
)
```

**(고급) background 변형은 task registry + liveness polling이 설정된 경우에만.** 그렇지 않으면 무산출 위험이 있으니 위 foreground 배치를 쓴다. background로 띄웠다면 산출물/트랜스크립트로 생존을 확인하고, 죽었거나 불확실하면 메인 스레드 순차로 폴백한다.

## File Operations

```python
Write(file_path="RESEARCH/.../file.md", content="...")
Read(file_path="RESEARCH/.../state.json")
Glob(pattern="RESEARCH/**/*.md")
```
