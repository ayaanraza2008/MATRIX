"""MATRIX Base Tool Adapter.
Defines the standard lifecycle, schema contracts, permission verification,
resource requirements, and verification hooks for all repository adapters.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
import time
from config.logging_config import get_logger

logger = get_logger("core.tool_adapters.base")


class AdapterExecutionResult(BaseModel):
    success: bool
    adapter_id: str
    operation: str
    data: Any = None
    verification: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class BaseAdapter(ABC):
    """Abstract Base Class for all MATRIX repository tool adapters."""

    def __init__(
        self,
        adapter_id: str,
        name: str,
        description: str,
        source_repo: str,
        category: str,
        version: str = "1.0.0"
    ):
        self.adapter_id = adapter_id
        self.name = name
        self.description = description
        self.source_repo = source_repo
        self.category = category
        self.version = version
        self.health_status = "healthy"
        self.test_results: Dict[str, Any] = {}
        self.logger = get_logger(f"adapter.{adapter_id}")

    @property
    @abstractmethod
    def supported_operations(self) -> List[str]:
        """List of operations supported by this adapter."""
        pass

    @property
    @abstractmethod
    def input_schema(self) -> Dict[str, Any]:
        """JSON-schema dictionary of input arguments for each operation."""
        pass

    @property
    @abstractmethod
    def output_schema(self) -> Dict[str, Any]:
        """JSON-schema dictionary of return structures."""
        pass

    @property
    def dependencies(self) -> List[str]:
        """List of Python / system dependencies required."""
        return []

    @property
    def permission_requirements(self) -> List[str]:
        """Permissions required (e.g. 'network', 'filesystem', 'system_metrics')."""
        return []

    @property
    def resource_requirements(self) -> Dict[str, Any]:
        """Estimated resource requirements on AMD Ryzen 7 5700U."""
        return {
            "ram_mb": 40,
            "cpu_threads": 1,
            "requires_gpu": False,
            "supports_avx2": True
        }

    async def initialize(self) -> bool:
        """Lifecycle hook to initialize adapter resources."""
        return True

    @abstractmethod
    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        """Execute the requested operation."""
        pass

    async def cancel(self) -> bool:
        """Cancel ongoing execution if running."""
        return True

    async def check_health(self) -> Dict[str, Any]:
        """Perform a live health probe on the underlying service/module."""
        return {
            "adapter_id": self.adapter_id,
            "status": self.health_status,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def cleanup(self) -> bool:
        """Release any acquired memory, file handles, or network connections."""
        return True

    async def verify_result(self, operation: str, result: Any) -> bool:
        """Post-execution verification to prove the action really succeeded."""
        if result is None:
            return False
        if isinstance(result, dict) and result.get("error"):
            return False
        return True

def unimplemented_result(
    adapter_id: str,
    operation: str,
    reason: str,
    execution_time_ms: float = 0.0,
) -> AdapterExecutionResult:
    """Explicit, honest failure for an adapter operation with no real backend.

    Adapters must never return ``success=True`` with fabricated data. When an operation
    is declared in ``supported_operations`` but has no implementation, callers get a
    verifiable failure instead of an invented payload.
    """
    return AdapterExecutionResult(
        success=False,
        adapter_id=adapter_id,
        operation=operation,
        error=f"NOT IMPLEMENTED: {reason}",
        verification={"implemented": False},
        execution_time_ms=execution_time_ms,
    )
