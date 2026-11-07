"""MATRIX Coding & Software Development Agent.
Inspects workspace codebases, runs test suites, checks syntax, and assists with refactoring.
"""
from typing import Dict, Any, List
import subprocess
import time
import ast
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult


class CodingAgent(BaseAgent):
    """Assists with software engineering, testing, debugging, and code analysis."""

    def __init__(self):
        super().__init__(
            name="coding",
            description="Analyzes code, validates syntax, runs test suites, and performs git operations.",
            max_autonomy_level=2
        )

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        raw_prompt = parameters.get("instruction", parameters.get("raw_prompt", "")).lower()

        # 1. Architectural Code Analysis (via Gravitas Adapter)
        if "architecture" in action.lower() or "inspect_code" in action.lower() or "analyze" in raw_prompt:
            file_path = parameters.get("file_path", "core/brain.py")
            return await self.execute_tool_adapter(
                adapter_id="adapter_gravitas",
                operation="inspect_code_architecture",
                parameters={"file_path": file_path}
            )

        # 2. Run Tests
        if "test" in action.lower() or "test" in raw_prompt:
            return await self._run_pytest(start_time)

        # 3. Syntax Validation
        if "syntax" in action.lower() or "validate" in raw_prompt:
            code_snippet = parameters.get("code", "")
            return self._validate_syntax(code_snippet, start_time)

        # 4. Workspace Inspection
        return await self._inspect_workspace(start_time)

    async def _run_pytest(self, start_time: float) -> AgentResult:
        """Run project test suite via pytest."""
        try:
            res = subprocess.run(
                ["python", "-m", "pytest", "tests/test_foundation.py", "-v"],
                capture_output=True,
                text=True,
                timeout=15
            )
            passed = res.returncode == 0
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=passed,
                agent_name=self.name,
                action_taken="run_tests",
                data={
                    "returncode": res.returncode,
                    "stdout": res.stdout[-400:] if res.stdout else "",
                    "passed": passed
                },
                verification={"tests_passed": passed, "verified": passed},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="run_tests",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    def _validate_syntax(self, code: str, start_time: float) -> AgentResult:
        """Validate Python code syntax using AST parsing."""
        latency = (time.perf_counter() - start_time) * 1000
        try:
            ast.parse(code)
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="validate_syntax",
                data={"valid": True, "message": "Syntax is clean and valid Python."},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except SyntaxError as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="validate_syntax",
                error=f"Syntax Error at line {e.lineno}: {e.msg}",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _inspect_workspace(self, start_time: float) -> AgentResult:
        """List active project files and python modules."""
        cwd = Path.cwd()
        py_files = [str(p.relative_to(cwd)) for p in cwd.glob("**/*.py") if ".venv" not in str(p)][:20]
        latency = (time.perf_counter() - start_time) * 1000

        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="inspect_workspace",
            data={"root": str(cwd), "python_files_count": len(py_files), "sample_files": py_files},
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
