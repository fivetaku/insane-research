#!/usr/bin/env python3
"""
Insane Research Orchestrator - State machine controller for research phases.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any, List


class ResearchPhase(Enum):
    INIT = "INIT"
    PHASE_1_SCOPING = "PHASE_1_SCOPING"
    PHASE_2_PLANNING = "PHASE_2_PLANNING"
    PHASE_3_QUERYING = "PHASE_3_QUERYING"
    PHASE_4_TRIANGULATION = "PHASE_4_TRIANGULATION"
    PHASE_5_SYNTHESIS = "PHASE_5_SYNTHESIS"
    PHASE_6_QA = "PHASE_6_QA"
    PHASE_7_OUTPUT = "PHASE_7_OUTPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PhaseStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ResearchState:
    def __init__(self, base_path: str = "RESEARCH"):
        self.base_path = Path(base_path)
        self.state: Dict[str, Any] = {}
        self.session_path: Path = Path(".")
        self._initialized = False

    def create_session(self, topic: str) -> str:
        session_id = (
            f"{self._sanitize_topic(topic)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        self.session_path = self.base_path / session_id
        self._initialized = True

        folders = [
            "artifacts/agent_results",
            "artifacts/drafts",
            "sources",
            "outputs/01_full_report",
            "outputs/02_end_user_guide",
            "outputs/03_developer_blueprint",
            "outputs/04_appendices",
            "website",
        ]

        for folder in folders:
            (self.session_path / folder).mkdir(parents=True, exist_ok=True)

        self.state = {
            "session_id": session_id,
            "topic": topic,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "status": ResearchPhase.INIT.value,
            "current_phase": 0,
            "requirements": {
                "focus": [],
                "output_format": "comprehensive_report",
                "scope": {},
                "sources": {},
                "audience": "",
                "special_requirements": [],
            },
            "plan": {"subtopics": [], "search_queries": {}, "agent_assignments": []},
            "progress": {
                "phase_1": PhaseStatus.PENDING.value,
                "phase_2": PhaseStatus.PENDING.value,
                "phase_3": PhaseStatus.PENDING.value,
                "phase_4": PhaseStatus.PENDING.value,
                "phase_5": PhaseStatus.PENDING.value,
                "phase_6": PhaseStatus.PENDING.value,
                "phase_7": PhaseStatus.PENDING.value,
            },
            "sources_count": 0,
            "artifacts": {},
            "errors": [],
        }

        self._save_state()
        self._create_readme()

        return session_id

    def load_session(self, session_id: str) -> bool:
        self.session_path = self.base_path / session_id
        state_file = self.session_path / "state.json"

        if not state_file.exists():
            return False

        with open(state_file, "r", encoding="utf-8") as f:
            self.state = json.load(f)

        self._initialized = True
        return True

    def _ensure_initialized(self):
        if not self._initialized:
            raise ValueError(
                "No active session. Call create_session() or load_session() first."
            )

    def _save_state(self):
        self._ensure_initialized()
        self.state["updated_at"] = datetime.now().isoformat()
        state_file = self.session_path / "state.json"

        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2, ensure_ascii=False)

    def _sanitize_topic(self, topic: str) -> str:
        sanitized = "".join(c if c.isalnum() or c in " -_" else "_" for c in topic)
        return sanitized.replace(" ", "_")[:50]

    def _create_readme(self):
        self._ensure_initialized()
        readme_content = f"""# Research: {self.state["topic"]}

## Session Info
- **Session ID**: {self.state["session_id"]}
- **Created**: {self.state["created_at"]}
- **Status**: {self.state["status"]}

## Folder Structure
```
{self.state["session_id"]}/
├── state.json
├── README.md
├── artifacts/
│   ├── research_plan.json
│   └── agent_results/
├── sources/
│   ├── sources.jsonl
│   └── bibliography.md
├── outputs/
│   ├── 00_executive_summary.md
│   ├── 01_full_report/
│   ├── 02_end_user_guide/
│   ├── 03_developer_blueprint/
│   └── 04_appendices/
└── website/
```

## Progress
| Phase | Status |
|-------|--------|
| 1. Question Scoping | {self.state["progress"]["phase_1"]} |
| 2. Retrieval Planning | {self.state["progress"]["phase_2"]} |
| 3. Iterative Querying | {self.state["progress"]["phase_3"]} |
| 4. Source Triangulation | {self.state["progress"]["phase_4"]} |
| 5. Knowledge Synthesis | {self.state["progress"]["phase_5"]} |
| 6. Quality Assurance | {self.state["progress"]["phase_6"]} |
| 7. Output & Packaging | {self.state["progress"]["phase_7"]} |

## Resume Command
```
/research-resume {self.state["session_id"]}
```
"""
        readme_path = self.session_path / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(readme_content)

    def start_phase(self, phase_num: int):
        self._ensure_initialized()
        phase_key = f"phase_{phase_num}"
        self.state["progress"][phase_key] = PhaseStatus.IN_PROGRESS.value
        self.state["current_phase"] = phase_num
        self.state["status"] = getattr(
            ResearchPhase, f"PHASE_{phase_num}_{self._get_phase_name(phase_num)}"
        ).value
        self._save_state()

    def complete_phase(self, phase_num: int, artifacts: Optional[Dict] = None):
        self._ensure_initialized()
        phase_key = f"phase_{phase_num}"
        self.state["progress"][phase_key] = PhaseStatus.COMPLETED.value

        if artifacts:
            self.state["artifacts"].update(artifacts)

        self._save_state()
        self._create_readme()

    def fail_phase(self, phase_num: int, error: str):
        self._ensure_initialized()
        phase_key = f"phase_{phase_num}"
        self.state["progress"][phase_key] = PhaseStatus.FAILED.value
        self.state["status"] = ResearchPhase.FAILED.value
        self.state["errors"].append(
            {
                "phase": phase_num,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )
        self._save_state()

    def _get_phase_name(self, phase_num: int) -> str:
        names = {
            1: "SCOPING",
            2: "PLANNING",
            3: "QUERYING",
            4: "TRIANGULATION",
            5: "SYNTHESIS",
            6: "QA",
            7: "OUTPUT",
        }
        return names.get(phase_num, "UNKNOWN")

    def get_current_phase(self) -> int:
        return self.state.get("current_phase", 0)

    def get_next_pending_phase(self) -> Optional[int]:
        for i in range(1, 8):
            phase_key = f"phase_{i}"
            status = self.state["progress"].get(phase_key)
            if status in [PhaseStatus.PENDING.value, PhaseStatus.IN_PROGRESS.value]:
                return i
        return None

    def is_completed(self) -> bool:
        return all(
            self.state["progress"][f"phase_{i}"] == PhaseStatus.COMPLETED.value
            for i in range(1, 8)
        )

    def set_requirements(self, requirements: Dict):
        self._ensure_initialized()
        self.state["requirements"].update(requirements)
        self._save_state()

    def set_plan(self, plan: Dict):
        self._ensure_initialized()
        self.state["plan"].update(plan)
        self._save_state()

    def add_source(self, source: Dict):
        self._ensure_initialized()
        sources_file = self.session_path / "sources" / "sources.jsonl"
        with open(sources_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(source, ensure_ascii=False) + "\n")
        self.state["sources_count"] += 1
        self._save_state()

    def get_sources(self) -> List[Dict]:
        self._ensure_initialized()
        sources_file = self.session_path / "sources" / "sources.jsonl"
        sources = []
        if sources_file.exists():
            with open(sources_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        sources.append(json.loads(line))
        return sources

    def save_artifact(self, name: str, content: str, subfolder: str = ""):
        self._ensure_initialized()
        if subfolder:
            artifact_path = self.session_path / "artifacts" / subfolder / name
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            artifact_path = self.session_path / "artifacts" / name

        with open(artifact_path, "w", encoding="utf-8") as f:
            f.write(content)

        self.state["artifacts"][name] = str(
            artifact_path.relative_to(self.session_path)
        )
        self._save_state()

    def save_output(self, name: str, content: str, subfolder: str = ""):
        self._ensure_initialized()
        if subfolder:
            output_path = self.session_path / "outputs" / subfolder / name
            output_path.parent.mkdir(parents=True, exist_ok=True)
        else:
            output_path = self.session_path / "outputs" / name

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

    def mark_completed(self):
        self._ensure_initialized()
        self.state["status"] = ResearchPhase.COMPLETED.value
        self._save_state()
        self._create_readme()


class ResearchOrchestrator:
    def __init__(self, base_path: str = "RESEARCH"):
        self.state_manager = ResearchState(base_path)
        self.base_path = Path(base_path)

    def start_research(self, topic: str) -> Dict[str, Any]:
        session_id = self.state_manager.create_session(topic)

        return {
            "session_id": session_id,
            "session_path": str(self.state_manager.session_path),
            "status": "initialized",
            "next_action": "clarify_requirements",
            "message": f"Research session created: {session_id}",
        }

    def resume_research(self, session_id: str) -> Dict[str, Any]:
        if not self.state_manager.load_session(session_id):
            return {"status": "error", "message": f"Session not found: {session_id}"}

        next_phase = self.state_manager.get_next_pending_phase()

        if next_phase is None:
            return {"status": "completed", "message": "Research already completed"}

        return {
            "session_id": session_id,
            "status": "resumed",
            "current_phase": next_phase,
            "next_action": f"execute_phase_{next_phase}",
            "message": f"Resuming from phase {next_phase}",
        }

    def get_status(self, session_id: str) -> Dict[str, Any]:
        if not self.state_manager.load_session(session_id):
            return {"status": "error", "message": "Session not found"}

        return {
            "session_id": session_id,
            "topic": self.state_manager.state["topic"],
            "status": self.state_manager.state["status"],
            "progress": self.state_manager.state["progress"],
            "sources_count": self.state_manager.state["sources_count"],
            "current_phase": self.state_manager.get_current_phase(),
        }

    def list_sessions(self) -> List[Dict]:
        sessions = []
        if not self.base_path.exists():
            return sessions

        for folder in self.base_path.iterdir():
            if folder.is_dir():
                state_file = folder / "state.json"
                if state_file.exists():
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    sessions.append(
                        {
                            "session_id": state["session_id"],
                            "topic": state["topic"],
                            "status": state["status"],
                            "created_at": state["created_at"],
                            "updated_at": state["updated_at"],
                        }
                    )

        return sorted(sessions, key=lambda x: x["updated_at"], reverse=True)


def init_research(topic: str, base_path: str = "RESEARCH") -> Dict:
    orchestrator = ResearchOrchestrator(base_path)
    return orchestrator.start_research(topic)


def resume_research(session_id: str, base_path: str = "RESEARCH") -> Dict:
    orchestrator = ResearchOrchestrator(base_path)
    return orchestrator.resume_research(session_id)


def get_research_status(session_id: str, base_path: str = "RESEARCH") -> Dict:
    orchestrator = ResearchOrchestrator(base_path)
    return orchestrator.get_status(session_id)


def list_research_sessions(base_path: str = "RESEARCH") -> List[Dict]:
    orchestrator = ResearchOrchestrator(base_path)
    return orchestrator.list_sessions()


if __name__ == "__main__":
    result = init_research("AI Detection Technologies 2025")
    print(json.dumps(result, indent=2))
