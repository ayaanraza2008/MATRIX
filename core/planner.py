"""MATRIX Execution Planner Module.
Defines execution steps, dependency ordering, risk tiers, and verification contracts.
"""
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class PlanStep(BaseModel):
    step_id: int
    title: str
    agent_name: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    risk_level: int = 1  # 0 to 4
    verification_hook: str  # e.g., 'check_process_running', 'check_file_exists'
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED, SKIPPED
    result: Optional[Any] = None
    error: Optional[str] = None


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    title: str
    goal: str
    steps: List[PlanStep]
    max_risk_level: int = 1
    requires_human_approval: bool = False
    status: str = "PENDING"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def mark_step_running(self, step_id: int):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "RUNNING"
                break

    def mark_step_completed(self, step_id: int, result: Any = None):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "COMPLETED"
                s.result = result
                break

    def mark_step_failed(self, step_id: int, error: str):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "FAILED"
                s.error = error
                self.status = "FAILED"
                break
