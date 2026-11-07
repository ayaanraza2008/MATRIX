"""MATRIX Base Agent Definition.
Abstract base class for all 16 specialized agents with typed schemas,
deterministic permission verification, execution tracking, and post-action verification hooks.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from config.settings import settings
from config.logging_config import get_logger


class AgentResult(BaseModel):
    success: bool
    agent_name: str
    action_taken: str
    data: Any = None
    verification: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseAgent(ABC):
    """Abstract base class for all specialized agents in MATRIX."""

    def __init__(self, name: str, description: str, max_autonomy_level: int = 2):
        self.name = name
        self.description = description
        self.max_autonomy_level = max_autonomy_level
        self.logger = get_logger(f"agent.{name}")

    def check_permission(self, action_risk_level: int) -> bool:
        """Verify whether action is authorized under MATRIX policy."""
        if action_risk_level > settings.security_level:
            self.logger.warning(
                f"Action blocked: Risk Level {action_risk_level} exceeds permitted Level {settings.security_level}"
            )
            return False
        return True

    async def execute_tool_adapter(
        self,
        adapter_id: str,
        operation: str,
        parameters: Dict[str, Any],
        is_user_confirmed: bool = False
    ) -> AgentResult:
        """Execute an operation through a repository tool adapter with verified results."""
        from core.tool_adapters.manager import adapter_manager
        start_time = datetime.now(timezone.utc)
        res = await adapter_manager.execute(
            adapter_id=adapter_id,
            operation=operation,
            parameters=parameters,
            is_user_confirmed=is_user_confirmed
        )
        return AgentResult(
            success=res.success,
            agent_name=self.name,
            action_taken=f"{adapter_id}:{operation}",
            data=res.data,
            verification=res.verification,
            error=res.error,
            execution_time_ms=res.execution_time_ms
        )

    @abstractmethod
    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        """Execute the requested tool action."""
        pass

    @abstractmethod
    async def verify(self, action: str, result: Any) -> bool:
        """Verify that the executed action actually succeeded on the device/subsystem."""
        pass
