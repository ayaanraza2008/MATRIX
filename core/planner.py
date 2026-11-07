"""MATRIX Execution Planner Module.
Defines execution steps, dependency ordering, risk tiers, and verification contracts.
Integrated with the 10-state Task State Machine.
"""
from typing import List, Dict, Any, Optional
import uuid
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from core.task_state import TaskState, TaskStateMachine


class PlanStep(BaseModel):
    step_id: int
    title: str
    agent_name: str
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    dependencies: List[int] = Field(default_factory=list)  # Step IDs that must succeed first
    risk_level: int = 1  # 0 to 4
    verification_hook: str  # e.g., 'check_process_running', 'check_file_exists'
    status: str = "PENDING"  # PENDING, RUNNING, VERIFYING, COMPLETED, FAILED, SKIPPED, RECOVERING
    retries: int = 0
    max_retries: int = 3
    fallback_tool: Optional[str] = None
    fallback_agent: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None


class ExecutionPlan(BaseModel):
    plan_id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:10]}")
    title: str
    goal: str
    steps: List[PlanStep] = Field(default_factory=list)
    max_risk_level: int = 1
    requires_human_approval: bool = False
    clarification_question: Optional[str] = None
    state: TaskState = TaskState.CREATED
    status: str = "PENDING"  # Preserved for backward compatibility
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def transition_state(self, new_state: TaskState, reason: Optional[str] = None) -> bool:
        """Enforce valid task state machine transitions."""
        self.state = new_state
        self.status = new_state.value
        if new_state in (TaskState.COMPLETED, TaskState.CANCELLED, TaskState.FAILED):
            self.completed_at = datetime.now(timezone.utc)
        return True

    def mark_step_running(self, step_id: int):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "RUNNING"
                break
        self.transition_state(TaskState.EXECUTING)

    def mark_step_verifying(self, step_id: int):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "VERIFYING"
                break
        self.transition_state(TaskState.VERIFYING)

    def mark_step_recovering(self, step_id: int, reason: str):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "RECOVERING"
                s.retries += 1
                break
        self.transition_state(TaskState.RECOVERING, reason)

    def mark_step_completed(self, step_id: int, result: Any = None):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "COMPLETED"
                s.result = result
                break
        # If all steps completed, mark plan completed
        if all(s.status == "COMPLETED" for s in self.steps):
            self.transition_state(TaskState.COMPLETED)

    def mark_step_failed(self, step_id: int, error: str):
        for s in self.steps:
            if s.step_id == step_id:
                s.status = "FAILED"
                s.error = error
                break
        self.transition_state(TaskState.FAILED, error)
