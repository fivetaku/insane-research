[English](README.md) | [한국어](README.ko.md) | 中文 | [日本語](README.ja.md) | [Español](README.es.md)

# insane-research

<div align="center">
  <img src="assets/hero.png" width="860" alt="insane-research 电影感主视觉">
</div>

> **insane-research — 具备来源验证与结构化产出的 AI 多智能体深度研究系统。**

一个问题，自动生成一份引用完备的综合研究报告。

[快速开始](#快速开始) • [为什么选择 insane-research？](#为什么选择-insane-research) • [工作原理](#工作原理) • [命令](#命令) • [产出](#产出结构) • [环境要求](#环境要求)

---

## 快速开始

### 1. 添加市场（只需一次）

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. 安装插件

```
/plugin install insane-research
```

### 3. 重启 Claude Code

缓存在启动时加载——安装后必须重启。

### 4. 开始研究

```
/insane-research AI coding assistants productivity impact
```

Claude 会先问几个界定范围的问题，然后部署并行研究智能体，交付一份结构化报告。

---

## 为什么选择 insane-research？

- **并行智能体，而非顺序搜索** —— 3-5 个智能体同时检索网络、学术与技术来源，大幅缩短研究时间
- **来源质量评级（A–E）** —— 每个来源都会被评级，从同行评审论文（A）到推测性帖子（E），你始终清楚自己在读什么
- **抗幻觉设计** —— 每条事实性论断都必须附带内联引用；关键论断需经至少 2 个独立来源交叉验证
- **可恢复会话** —— 研究状态保存在 `state.json` 中；会话中断后可随时从原处继续
- **完整交付物** —— 执行摘要、分章节完整报告、参考文献，以及可选的交互式网站——全部自动生成

---

## 工作原理

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

## 命令

| 命令 | 说明 |
|---------|------|
| `/insane-research [topic]` | 开始新的研究会话 |
| `/insane-research resume [session_id]` | 恢复之前的会话 |
| `/insane-research status` | 查看所有会话进度 |
| `/insane-research query` | 启动结构化查询构建器 |
| `/insane-research refs <主题>` | 轻量模式：只收集参考图片（少量候选页面＋大图，不生成报告） |
| `/insane-research` | 打开交互式菜单 |

### 自然语言触发

```
deep research on [topic]
research [topic]
[topic] 리서치해줘
딥리서치 [주제]
심층 연구 [주제]
```

---

## 智能体

Phase 3 期间会并行运行三类智能体：

| 智能体 | 数量 | 侧重 |
|-------|-------|-------|
| 网络研究 | 2–3 | 最新新闻、趋势、市场数据 |
| 学术 / 技术 | 1–2 | 论文、规范、官方文档 |
| 交叉验证 | 1 | 关键论断的事实核查 |

---

## 来源质量评级

| 等级 | 类型 | 示例 |
|-------|------|---------|
| **A** | 同行评审、系统综述 | Nature、Lancet、IEEE |
| **B** | 官方文档、临床指南 | FDA、W3C、WHO |
| **C** | 专家意见、行业报告 | Gartner、行业会议 |
| **D** | 预印本、白皮书 | arXiv、公司博客 |
| **E** | 轶事性、推测性 | 社交媒体、论坛 |

---

## 产出结构

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

## 环境要求

- [Claude Code](https://docs.anthropic.com/claude-code) CLI
- WebSearch（内置）或任一网络搜索 MCP 服务器

### 可选 MCP 服务器（增强搜索覆盖）

- Firecrawl
- Google Search MCP
- Exa Search

---

## 许可证

MIT

---

<div align="center">

**引用来源的研究。每一次。**

</div>
