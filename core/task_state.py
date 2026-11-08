"""MATRIX Task State Machine.
Defines explicit lifecycle states and valid transitions for autonomous multi-step tasks.
"""
from enum import Enum
from typing import Set, Dict, Optional
import time
from pydantic import BaseModel, Field


class TaskState(str, Enum):
    """Explicit task lifecycle states as required by MATRIX Central Intelligence."""
    CREATED = "CREATED"
    PLANNING = "PLANNING"
    WAITING_FOR_INPUT = "WAITING_FOR_INPUT"
    READY = "READY"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    RECOVERING = "RECOVERING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    INTERRUPTED = "INTERRUPTED"


# Valid state transitions matrix
VALID_TRANSITIONS: Dict[TaskState, Set[TaskState]] = {
    TaskState.CREATED: {TaskState.PLANNING, TaskState.CANCELLED},
    TaskState.PLANNING: {TaskState.READY, TaskState.WAITING_FOR_INPUT, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.WAITING_FOR_INPUT: {TaskState.PLANNING, TaskState.READY, TaskState.CANCELLED},
    TaskState.READY: {TaskState.EXECUTING, TaskState.CANCELLED},
    TaskState.EXECUTING: {TaskState.VERIFYING, TaskState.RECOVERING, TaskState.FAILED, TaskState.CANCELLED, TaskState.INTERRUPTED},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.RECOVERING, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.RECOVERING: {TaskState.EXECUTING, TaskState.WAITING_FOR_INPUT, TaskState.FAILED, TaskState.CANCELLED, TaskState.INTERRUPTED},
    TaskState.COMPLETED: set(),  # Terminal state
    TaskState.FAILED: {TaskState.RECOVERING},  # May attempt recovery if requested
    TaskState.CANCELLED: set(),  # Terminal state
    TaskState.INTERRUPTED: set(),  # Terminal state
}


class TaskStateTransition(BaseModel):
    """Records each state change with timestamp and reason."""
    from_state: TaskState
    to_state: TaskState
    timestamp: float = Field(default_factory=time.time)
    reason: Optional[str] = None


class TaskStateMachine:
    """Manages state transitions for a task instance with strict transition enforcement."""

    def __init__(self, initial_state: TaskState = TaskState.CREATED):
        self.current_state: TaskState = initial_state
        self.history: list[TaskStateTransition] = []

    def can_transition_to(self, new_state: TaskState) -> bool:
        """Verify if transition is logically permitted."""
        return new_state in VALID_TRANSITIONS.get(self.current_state, set())

    def transition_to(self, new_state: TaskState, reason: Optional[str] = None) -> bool:
        """Perform transition if valid, updating history."""
        if not self.can_transition_to(new_state):
            # Allow force reset only if cancelled
            if new_state == TaskState.CANCELLED:
                pass
            else:
                return False

        transition = TaskStateTransition(
            from_state=self.current_state,
            to_state=new_state,
            reason=reason
        )
        self.history.append(transition)
        self.current_state = new_state
        return True

    @property
    def is_terminal(self) -> bool:
        return self.current_state in (TaskState.COMPLETED, TaskState.CANCELLED)

    @property
    def is_active(self) -> bool:
        return self.current_state in (
            TaskState.CREATED, TaskState.PLANNING, TaskState.READY,
            TaskState.EXECUTING, TaskState.VERIFYING, TaskState.RECOVERING
        )
