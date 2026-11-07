"""MATRIX Developer Studio API Route.
Provides Python code syntax validation, sandbox execution, and test suite runners.
"""
from fastapi import APIRouter
from pydantic import BaseModel
import subprocess
import time
import ast
import sys

router = APIRouter(prefix="/developer", tags=["Developer Studio"])


class CodeRunRequest(BaseModel):
    code: str


class TestRunRequest(BaseModel):
    test_file: str = "tests/test_foundation.py"


@router.post("/validate")
async def validate_syntax(payload: CodeRunRequest):
    """Validate Python syntax via AST."""
    try:
        ast.parse(payload.code)
        return {"valid": True, "message": "Syntax is clean and valid Python."}
    except SyntaxError as e:
        return {"valid": False, "error": f"SyntaxError at line {e.lineno}: {e.msg}"}


@router.post("/execute")
async def execute_code(payload: CodeRunRequest):
    """Execute Python code snippet in an isolated subprocess."""
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", payload.code],
            capture_output=True,
            text=True,
            timeout=5
        )
        latency = (time.perf_counter() - start_time) * 1000
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "latency_ms": round(latency, 2)
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out after 5 seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/run-tests")
async def run_tests(payload: TestRunRequest):
    """Run pytest suite on specified test file."""
    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", payload.test_file, "-v"],
            capture_output=True,
            text=True,
            timeout=25
        )
        latency = (time.perf_counter() - start_time) * 1000
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "latency_ms": round(latency, 2)
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
