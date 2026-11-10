"""MATRIX Goal Manager.
Coordinates persistent long-term goals, autonomous sub-goal decomposition,
milestone verification, and lifecycle execution.
"""
from typing import Dict, Any, List, Optional
import time
import uuid
from pydantic import BaseModel, Field
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.autonomy.goal_manager")


class SubGoal(BaseModel):
    subgoal_id: str = Field(default_factory=lambda: f"sub_{uuid.uuid4().hex[:6]}")
    title: str
    assigned_agent: str
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED
    result: Optional[str] = None
    verification_criteria: str
    completed_at: Optional[float] = None


class Goal(BaseModel):
    goal_id: str = Field(default_factory=lambda: f"goal_{uuid.uuid4().hex[:8]}")
    title: str
    description: str
    priority: int = 1  # 1 (Highest) to 5 (Lowest)
    status: str = "ACTIVE"  # ACTIVE, PAUSED, COMPLETED, FAILED, CANCELLED
    subgoals: List[SubGoal] = Field(default_factory=list)
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    progress_percent: int = 0
    assigned_agents: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


class GoalManager:
    """Manages long-running goals across sessions with persistent storage."""

    def __init__(self):
        self._goals_file = settings.data_dir / "goals.json"
        self._goals: Dict[str, Goal] = {}
        self._load_goals()

    def _load_goals(self):
        import json
        if self._goals_file.exists():
            try:
                data = json.loads(self._goals_file.read_text(encoding="utf-8"))
                for g_data in data:
                    g = Goal(**g_data)
                    self._goals[g.goal_id] = g
                logger.info(f"Loaded {len(self._goals)} persistent goals from disk.")
            except Exception as e:
                logger.warning(f"Could not load goals from {self._goals_file}: {e}")

    def _save_goals(self):
        import json
        try:
            self._goals_file.parent.mkdir(parents=True, exist_ok=True)
            serializable = [g.model_dump() for g in self._goals.values()]
            self._goals_file.write_text(json.dumps(serializable, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not persist goals to disk: {e}")

    def create_goal(
        self,
        title: str,
        description: str,
        subgoals: Optional[List[Dict[str, str]]] = None,
        priority: int = 2,
        tags: Optional[List[str]] = None
    ) -> Goal:
        """Create a new autonomous goal with optional structured subgoals."""
        parsed_subgoals = []
        agents = set()
        if subgoals:
            for sg in subgoals:
                agent = sg.get("assigned_agent", "core")
                agents.add(agent)
                parsed_subgoals.append(SubGoal(
                    title=sg.get("title", ""),
                    assigned_agent=agent,
                    verification_criteria=sg.get("verification_criteria", "Output verified")
                ))

        goal = Goal(
            title=title,
            description=description,
            priority=priority,
            subgoals=parsed_subgoals,
            assigned_agents=list(agents) if agents else ["core"],
            tags=tags or ["general"]
        )
        self._goals[goal.goal_id] = goal
        self._save_goals()
        logger.info(f"Goal '{title}' registered with ID: {goal.goal_id} ({len(parsed_subgoals)} subgoals)")
        return goal

    def update_subgoal_progress(
        self,
        goal_id: str,
        subgoal_id: str,
        status: str,
        result: Optional[str] = None
    ) -> Optional[Goal]:
        """Update progress on a specific subgoal and recompute completion percentage."""
        goal = self._goals.get(goal_id)
        if not goal:
            return None

        for sg in goal.subgoals:
            if sg.subgoal_id == subgoal_id:
                sg.status = status
                if result:
                    sg.result = result
                if status == "COMPLETED":
                    sg.completed_at = time.time()
                break

        # Recompute percentage
        if goal.subgoals:
            completed = sum(1 for sg in goal.subgoals if sg.status == "COMPLETED")
            goal.progress_percent = int((completed / len(goal.subgoals)) * 100)
            if goal.progress_percent == 100:
                goal.status = "COMPLETED"

        goal.updated_at = time.time()
        self._save_goals()
        return goal

    def list_goals(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active or filtered goals."""
        results = []
        for g in self._goals.values():
            if status is None or g.status == status:
                results.append(g.model_dump())
        return sorted(results, key=lambda x: (x["priority"], -x["updated_at"]))

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        return self._goals.get(goal_id)


# Global Goal Manager singleton
goal_manager = GoalManager()
