[English](README.md) | [한국어](README.ko.md) | [中文](README.zh.md) | [日本語](README.ja.md) | Español

# insane-research

<div align="center">
  <img src="assets/hero.png" width="860" alt="héroe cinematográfico de insane-research">
</div>

> **insane-research — investigación profunda multiagente impulsada por IA, con verificación de fuentes y salidas estructuradas.**

Convierte una sola pregunta en un informe de investigación completo y respaldado por citas — automáticamente.

[Inicio rápido](#inicio-rápido) • [¿Por qué insane-research?](#por-qué-insane-research) • [Cómo funciona](#cómo-funciona) • [Comandos](#comandos) • [Salida](#estructura-de-salida) • [Requisitos](#requisitos)

---

## Inicio rápido

### 1. Añade el marketplace (solo una vez)

```
/plugin marketplace add https://github.com/fivetaku/gptaku_plugins.git
```

### 2. Instala el plugin

```
/plugin install insane-research
```

### 3. Reinicia Claude Code

La caché se carga al arrancar — es necesario reiniciar después de instalar.

### 4. Empieza a investigar

```
/insane-research AI coding assistants productivity impact
```

Claude hará algunas preguntas para acotar el alcance, luego desplegará agentes de investigación en paralelo y entregará un informe estructurado.

---

## ¿Por qué insane-research?

- **Agentes en paralelo, no búsquedas secuenciales** — 3-5 agentes trabajan simultáneamente sobre fuentes web, académicas y técnicas, reduciendo notablemente el tiempo de investigación
- **Calificación de calidad de fuentes (A–E)** — cada fuente se califica desde artículos revisados por pares (A) hasta publicaciones especulativas (E), así siempre sabes qué estás leyendo
- **Resistente a alucinaciones** — cada afirmación factual exige una cita en línea; las afirmaciones clave se verifican de forma cruzada con al menos 2 fuentes independientes
- **Sesiones reanudables** — el estado de la investigación se guarda en `state.json`; retoma donde lo dejaste si una sesión se interrumpe
- **Entregables completos** — resumen ejecutivo, informe completo por secciones, bibliografía y un sitio web interactivo opcional — todo generado automáticamente

---

## Cómo funciona

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

## Comandos

| Comando | Descripción |
|---------|-------------|
| `/insane-research [topic]` | Inicia una nueva sesión de investigación |
| `/insane-research resume [session_id]` | Reanuda una sesión anterior |
| `/insane-research status` | Muestra el progreso de todas las sesiones |
| `/insane-research query` | Lanza el constructor de consultas estructuradas |
| `/insane-research refs <tema>` | Modo ligero: solo recopila imágenes de referencia (algunas páginas + sus imágenes grandes, sin informe) |
| `/insane-research` | Abre el menú interactivo |

### Disparadores en lenguaje natural

```
deep research on [topic]
research [topic]
[topic] 리서치해줘
딥리서치 [주제]
심층 연구 [주제]
```

---

## Agentes

Durante la Fase 3 se ejecutan en paralelo tres tipos de agentes:

| Agente | Cantidad | Enfoque |
|-------|-------|-------|
| Investigación web | 2–3 | Últimas noticias, tendencias, datos de mercado |
| Académico / técnico | 1–2 | Artículos, especificaciones, documentación oficial |
| Referencia cruzada | 1 | Verificación de las afirmaciones clave |

---

## Calificación de calidad de fuentes

| Grado | Tipo | Ejemplos |
|-------|------|---------|
| **A** | Revisado por pares, revisiones sistemáticas | Nature, Lancet, IEEE |
| **B** | Documentación oficial, guías clínicas | FDA, W3C, WHO |
| **C** | Opinión experta, informes del sector | Gartner, conferencias |
| **D** | Preprints, white papers | arXiv, blogs corporativos |
| **E** | Anecdótico, especulativo | Redes sociales, foros |

---

## Estructura de salida

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

## Requisitos

- CLI de [Claude Code](https://docs.anthropic.com/claude-code)
- WebSearch (integrado) o un servidor MCP de búsqueda web

### Servidores MCP opcionales (mejoran la cobertura de búsqueda)

- Firecrawl
- Google Search MCP
- Exa Search

---

## Licencia

MIT

---

<div align="center">

**Investigación que cita sus fuentes. Siempre.**

</div>
