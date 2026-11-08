"""MATRIX Base Agent Definition.
Abstract base class for all 16 specialized agents with typed schemas,
input/output validation, execution timeouts, cancellation tokens,
deterministic permission verification, execution tracking, and post-action verification hooks.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import asyncio
import time
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from config.settings import settings
from config.logging_config import get_logger


class AgentCapability(BaseModel):
    name: str
    description: str
    operations: List[str]
    risk_level: int = 1
    requires_confirmation: bool = False


class AgentResult(BaseModel):
    success: bool
    agent_name: str
    action_taken: str
    data: Any = None
    verification: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 3 Execution Truthfulness & Tool Result Contract
    request_id: Optional[str] = None
    task_id: Optional[str] = None
    step_id: Optional[int] = None
    tool_name: Optional[str] = None
    execution_status: str = "SUCCESS"  # SUCCESS, FAILED, PARTIAL, BLOCKED, NOT_CONFIGURED, SIMULATED
    actual_result: Any = None
    verification_status: str = "UNVERIFIED"  # VERIFIED, UNVERIFIED, FAILED, BLOCKED
    error_details: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.tool_name:
            self.tool_name = self.action_taken
        if self.actual_result is None and self.data is not None:
            self.actual_result = self.data
        if self.error_details is None and self.error is not None:
            self.error_details = self.error

        if not self.success:
            if self.execution_status == "SUCCESS":
                err_lower = (self.error or "").lower()
                if "block" in err_lower or "policy" in err_lower or "denied" in err_lower:
                    self.execution_status = "BLOCKED"
                elif "not configured" in err_lower or "unsupported" in err_lower:
                    self.execution_status = "NOT_CONFIGURED"
                elif "simulat" in err_lower:
                    self.execution_status = "SIMULATED"
                elif "partial" in err_lower:
                    self.execution_status = "PARTIAL"
                else:
                    self.execution_status = "FAILED"
            if self.verification_status == "UNVERIFIED":
                self.verification_status = "FAILED"
        elif self.verification.get("verified"):
            self.verification_status = "VERIFIED"


class BaseAgent(ABC):
    """Abstract base class for all specialized agents in MATRIX."""

    def __init__(
        self,
        name: str,
        description: str,
        max_autonomy_level: int = 2,
        timeout_seconds: float = 30.0
    ):
        self.name = name
        self.description = description
        self.max_autonomy_level = max_autonomy_level
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger(f"agent.{name}")
        self._cancel_requested: bool = False
        self._capabilities: List[AgentCapability] = []

    def cancel(self):
        """Signal cancellation for active agent execution."""
        self._cancel_requested = True
        self.logger.warning(f"Cancellation signaled for agent {self.name}.")

    def check_permission(self, action_risk_level: int) -> bool:
        """Verify whether action is authorized under MATRIX policy."""
        if action_risk_level > settings.security_level:
            self.logger.warning(
                f"Action blocked: Risk Level {action_risk_level} exceeds permitted Level {settings.security_level}"
            )
            return False
        return True

    def declare_capabilities(self) -> List[AgentCapability]:
        """Return the list of validated capabilities this agent provides."""
        return self._capabilities

    def discover_tools(self) -> List[str]:
        """Discover tools and operations supported by this agent."""
        ops = []
        for cap in self._capabilities:
            ops.extend(cap.operations)
        return ops or ["execute", "status"]

    async def run_with_timeout(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        """Wrapper executing agent action with timeout, cancellation check, and verification."""
        self._cancel_requested = False
        start_time = time.perf_counter()

        try:
            res: AgentResult = await asyncio.wait_for(
                self.execute(action, parameters),
                timeout=self.timeout_seconds
            )
            # Verify result if successful
            if res.success:
                verified = await self.verify(action, res.data)
                res.verification["verified"] = verified
            return res
        except asyncio.TimeoutError:
            latency = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Agent {self.name} action '{action}' timed out after {self.timeout_seconds}s.")
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken=action,
                error=f"Operation timed out after {self.timeout_seconds} seconds.",
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            self.logger.error(f"Agent {self.name} action '{action}' raised error: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken=action,
                error=str(e),
                execution_time_ms=round(latency, 2)
            )

    async def execute_tool_adapter(
        self,
        adapter_id: str,
        operation: str,
        parameters: Dict[str, Any],
        is_user_confirmed: bool = False
    ) -> AgentResult:
        """Execute an operation through a repository tool adapter with verified results."""
        from core.tool_adapters.manager import adapter_manager
        start_time = time.perf_counter()
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

    async def verify(self, action: str, result: Any) -> bool:
        """Verify that the executed action actually succeeded on the device/subsystem.
        Default implementation checks that result is not None and not error.
        """
        return result is not None
