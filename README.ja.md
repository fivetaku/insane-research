[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | 日本語 | [Español](README.es.md)

# insane-research

<div align="center">
  <img src="assets/hero.png" width="860" alt="insane-research シネマティックヒーロー">
</div>

> **insane-research — ソース検証と構造化された成果物を備えた、AI マルチエージェント・ディープリサーチ。**

質問ひとつから、引用に裏付けられた包括的なリサーチレポートを——自動で。

[クイックスタート](#クイックスタート) • [なぜ insane-research？](#なぜ-insane-research) • [仕組み](#仕組み) • [コマンド](#コマンド) • [成果物](#成果物の構造) • [必要環境](#必要環境)

---

## クイックスタート

### 1. マーケットプレイスを追加（最初の一度だけ）

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. プラグインをインストール

```
/plugin install insane-research
```

### 3. Claude Code を再起動

キャッシュは起動時に読み込まれます——インストール後は再起動が必要です。

### 4. リサーチを開始

```
/insane-research AI coding assistants productivity impact
```

Claude がいくつかのスコーピング質問をした後、並列リサーチエージェントを展開し、構造化されたレポートを届けます。

---

## なぜ insane-research？

- **逐次検索ではなく並列エージェント** —— 3〜5 体のエージェントがウェブ・学術・技術ソースを同時に横断し、リサーチ時間を大幅に短縮
- **ソース品質評価（A–E）** —— すべてのソースを査読済み論文（A）から推測的な投稿（E）まで格付け。いま読んでいるものの信頼度が常にわかる
- **ハルシネーション耐性** —— すべての事実主張にインライン引用を必須化。重要な主張は少なくとも 2 つの独立ソースで相互検証
- **再開可能なセッション** —— リサーチ状態は `state.json` に保存。セッションが中断しても続きから再開できる
- **完全な成果物** —— エグゼクティブサマリー、セクション構成の完全レポート、参考文献、オプションのインタラクティブウェブサイトまで——すべて自動生成

---

## 仕組み

```
User query
    │
    ▼
Phase 1: Question Scoping
  └─ AskUserQuestion → focus, depth, audience, sources
    │
    ▼
Phase 2: Retrieval Planning
  └─ Break into 3-5 subtopics → search query generation → plan approval
    │
    ▼
Phase 3: Iterative Querying  ←──────────────────┐
  ├─ Web Research Agent (x2-3)                  │
  ├─ Academic/Technical Agent (x1-2)            │ refine if gaps
  └─ Cross-Reference Agent (x1)                 │
    │                                            │
    ▼                                            │
Phase 4: Source Triangulation ─────────────────-┘
  └─ Cross-verify key claims (≥2 sources) → A–E quality rating
    │
    ▼
Phase 5: Knowledge Synthesis
  └─ Structure → write sections → inline citations
    │
    ▼
Phase 6: Quality Assurance
  └─ Hallucination check → citation verification → completeness
    │
    ▼
Phase 7: Output & Packaging
  └─ Executive summary + full report + bibliography + website (optional)
```

---

## コマンド

| コマンド | 説明 |
|---------|------|
| `/insane-research [topic]` | 新しいリサーチセッションを開始 |
| `/insane-research resume [session_id]` | 前回のセッションを再開 |
| `/insane-research status` | すべてのセッションの進捗を表示 |
| `/insane-research query` | 構造化クエリビルダーを起動 |
| `/insane-research refs <テーマ>` | ライトモード: 参考画像だけを収集（候補ページ数件＋大きな画像、レポートなし） |
| `/insane-research` | インタラクティブメニューを開く |

### 自然言語トリガー

```
deep research on [topic]
research [topic]
[topic] 리서치해줘
딥리서치 [주제]
심층 연구 [주제]
```

---

## エージェント

Phase 3 では 3 種類のエージェントが並列で動作します：

| エージェント | 数 | 担当 |
|-------|-------|-------|
| ウェブリサーチ | 2–3 | 最新ニュース、トレンド、市場データ |
| 学術 / 技術 | 1–2 | 論文、仕様、公式ドキュメント |
| 相互参照 | 1 | 重要な主張のファクトチェック |

---

## ソース品質評価

| 等級 | 種類 | 例 |
|-------|------|---------|
| **A** | 査読済み、系統的レビュー | Nature、Lancet、IEEE |
| **B** | 公式ドキュメント、臨床ガイドライン | FDA、W3C、WHO |
| **C** | 専門家の見解、業界レポート | Gartner、カンファレンス |
| **D** | プレプリント、ホワイトペーパー | arXiv、企業ブログ |
| **E** | 逸話的、推測的 | ソーシャルメディア、フォーラム |

---

## 成果物の構造

```
RESEARCH/{topic}_{timestamp}/
├── state.json                    # Session state (for resume)
├── README.md                     # Navigation guide
├── outputs/
│   ├── 00_executive_summary.md   # 3–5 page summary
│   ├── 01_full_report/           # Full sectioned report
│   ├── 02_appendices/            # Supporting material
│   └── comparison_data.json      # Structured comparison data
├── sources/
│   ├── sources.jsonl             # Collected sources
│   ├── bibliography.md           # Formatted bibliography
│   └── quality_report.md         # Source quality ratings
└── website/                      # (optional) Interactive presentation
    ├── index.html
    ├── styles.css
    └── script.js
```

---

## 必要環境

- [Claude Code](https://docs.anthropic.com/claude-code) CLI
- WebSearch（ビルトイン）またはウェブ検索 MCP サーバー

### オプションの MCP サーバー（検索カバレッジを強化）

- Firecrawl
- Google Search MCP
- Exa Search

---

## ライセンス

MIT

---

<div align="center">

**出典を引用するリサーチを。毎回、必ず。**

</div>
