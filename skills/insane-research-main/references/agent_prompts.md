# Agent Prompt Templates

## General Research Agent
```
Research [specific aspect] of [main topic].

Focus on finding:
- Recent information (prioritize last 2 years)
- Authoritative sources
- Specific data/statistics
- Multiple perspectives

For EVERY factual claim, provide:
- Direct quote or data point
- Source URL
- Author/organization
- Publication date
- Confidence rating (High/Medium/Low)

Return structured findings with all source URLs.
```

## Technical Research Agent
```
Find technical/academic information about [topic].

Look for:
- Peer-reviewed papers
- Technical specifications
- Methodologies and frameworks
- Scientific evidence

Include proper academic citations with DOI/URLs.
```

## Verification Agent
```
Verify the following claims about [topic]:
[List key claims to verify]

Use multiple search queries to find:
- Supporting evidence
- Contradicting information
- Original sources

Rate confidence: High/Medium/Low for each claim.
Explain any contradictions found.
Never confirm without sources.
```

## Agent Deployment Pattern

```python
# Deploy agents for subtopics using Task tool — THROTTLE to 2-3 concurrent per batch
# (Rate-Limit & Reliability Guard in SKILL.md): liveness check + sequential fallback
Task(subagent_type="Explore", prompt="Research current state of [subtopic1]...")
Task(subagent_type="Explore", prompt="Research challenges in [subtopic2]...")
Task(subagent_type="Explore", prompt="Find official documentation for [subtopic3]...")
Task(subagent_type="Explore", prompt="Find academic papers on [subtopic4]...")
Task(subagent_type="Explore", prompt="Verify key claims: [list claims]...")

# Launch agents in throttled batches (2-3 Task calls per response, await each batch) —
# NOT one large fan-out (it rate-limits and background agents can silently die)
# Collect results when each agent completes
```

---

## Graph of Thoughts Integration

The research process uses Graph of Thoughts (GoT) for complex reasoning:

1. **Modeling Research as Graph Operations**: Each research step becomes a node
2. **Parallel Processing**: Multiple research paths explored simultaneously
3. **Scoring & Optimization**: Information quality scored and optimized
4. **Backtracking**: Poor research paths abandoned for better alternatives

### GoT Operations:
- **Generate**: Create search queries and hypotheses
- **Score**: Evaluate information quality and relevance
- **GroundTruth**: Verify facts against authoritative sources
- **Aggregate**: Combine findings from multiple sources
- **Improve**: Refine research questions based on findings
