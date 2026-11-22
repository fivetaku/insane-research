# Research-type skeletons (long-form option only)

The default long-form skeleton is 5 sections: introduction / current_landscape / challenges /
future_outlook / conclusions. Use the patterns below only when the user explicitly asks for a different
research type. The table is a set of examples for generating section names on the fly, not a menu.

## Generation rules
- Fill five slots from the user's topic: introduction / core analysis / domain-specific (comparison,
  forecast, causes…) / limits and risks / conclusion.
- Do not copy the section names verbatim — rename them for the user's topic.

## Example patterns

| Research Type | 5-section pattern | Fits |
|---|---|---|
| **Exploratory** | introduction / landscape / opportunities / challenges / conclusions | new market or technology |
| **Comparative** | introduction / criteria / comparison_matrix / recommendation / conclusions | tool or product comparison |
| **Predictive** | introduction / current_state / trends / scenarios / risks_and_recommendations | forecasts, roadmaps |
| **Analytical** | introduction / problem / causes / effects / conclusions | incident or causal analysis |
| **Generic (default)** | introduction / current_landscape / challenges / future_outlook / conclusions | comprehensive research |

Example: "X 시장의 한국 vs 일본 차이" → Comparative → `introduction / 시장규모비교 / 사용자행동차이 / 규제차이 / 진입전략추천`.

## Procedure
1. In Phase 1, estimate the closest pattern from the user's wording.
2. Generate five section names for the user's topic.
3. Confirm with the user ("이 리서치는 [Comparative] 패턴에 가까워 보입니다. 5섹션을 [...]로 진행할까요? 또는 기본 5섹션으로?").
4. Confirmed → use the generated skeleton; unclear or not specified → default 5 sections.
5. Record the final skeleton in `state.json` `report_skeleton` (resumable).

Do not choose a type without confirmation, and do not add new rows to this table. The verification
contracts (2-source minimum, A-E ratings, ledger gates) apply unchanged whatever skeleton is used.
