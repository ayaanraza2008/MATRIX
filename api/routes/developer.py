"""MATRIX Developer Studio API Route.
Provides Python code syntax validation, sandbox execution, test suite runners,
project scaffolding (Python, JS/TS, Android), and project ZIP exports.

Security posture
----------------
* Execution endpoints are disabled unless ``MATRIX_DEVELOPER_MODE=true``.
* Every endpoint that touches the filesystem is authenticated for non-local clients
  and constrained to the workspace root via :func:`security.path_guard.resolve_within`.
* Child processes inherit a scrubbed environment (no API keys / tokens).
"""
from __future__ import annotations

import ast
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from config.settings import settings
from core.device_auth import security_rate_limiter
from security.authentication.api_access import (
    require_authenticated_client,
    require_developer_mode,
)
from security.path_guard import PathTraversalError, is_safe_name, resolve_within

router = APIRouter(prefix="/developer", tags=["Developer Studio"])

_SECRET_MARKERS = ("TOKEN", "KEY", "SECRET", "PASSWORD", "CREDENTIAL")


class CodeRunRequest(BaseModel):
    code: str = Field(..., max_length=20_000)


class TestRunRequest(BaseModel):
    test_file: str = "tests/test_foundation.py"


class ProjectScaffoldRequest(BaseModel):
    project_name: str
    project_type: str = "python"  # 'python', 'typescript', 'android'
    description: Optional[str] = "MATRIX Generated Project"


def _scrubbed_env() -> dict:
    """Copy the environment without credentials."""
    return {
        k: v
        for k, v in os.environ.items()
        if not any(marker in k.upper() for marker in _SECRET_MARKERS)
    }


def _projects_root() -> Path:
    root = settings.data_dir / "test_workspace" / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


async def limit_developer_execution(request: Request) -> None:
    """Throttle the code-execution endpoints to 10 requests/minute per client."""
    client = request.client.host if request.client else "unknown"
    if not security_rate_limiter.check_rate_limit(
        f"developer_exec_{client}", max_requests=10, window_seconds=60
    ):
        raise HTTPException(
            status_code=429,
            detail="Developer execution rate limit exceeded (10 per minute).",
        )


def _validated_project_dir(project_name: str) -> Path:
    if not is_safe_name(project_name):
        raise HTTPException(status_code=400, detail="Invalid project name.")
    try:
        return resolve_within(_projects_root(), project_name)
    except PathTraversalError:
        raise HTTPException(status_code=400, detail="Invalid project name.")


@router.post("/validate")
async def validate_syntax(payload: CodeRunRequest):
    """Validate Python syntax via AST (no execution)."""
    try:
        ast.parse(payload.code)
        return {"valid": True, "message": "Syntax is clean and valid Python."}
    except SyntaxError as e:
        return {"valid": False, "error": f"SyntaxError at line {e.lineno}: {e.msg}"}


@router.post(
    "/execute",
    dependencies=[
        Depends(require_authenticated_client),
        Depends(require_developer_mode),
        Depends(limit_developer_execution),
    ],
)
async def execute_code(payload: CodeRunRequest):
    """Execute a Python code snippet in an isolated subprocess."""
    start_time = time.perf_counter()
    sandbox = settings.data_dir / "test_workspace" / "exec"
    sandbox.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", payload.code],
            capture_output=True,
            text=True,
            timeout=8,
            cwd=str(sandbox),
            env=_scrubbed_env(),
        )
        latency = (time.perf_counter() - start_time) * 1000
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "latency_ms": round(latency, 2),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Execution timed out after 8 seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post(
    "/run-tests",
    dependencies=[
        Depends(require_authenticated_client),
        Depends(require_developer_mode),
        Depends(limit_developer_execution),
    ],
)
async def run_tests(payload: TestRunRequest):
    """Run one of the repository's own pytest files."""
    tests_root = settings.base_dir / "tests"
    try:
        target = resolve_within(tests_root, payload.test_file.removeprefix("tests/"))
    except PathTraversalError:
        raise HTTPException(status_code=400, detail="Test file must live inside tests/.")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Test file not found.")

    start_time = time.perf_counter()
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", str(target), "-v"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(settings.base_dir),
            env=_scrubbed_env(),
        )
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "returncode": proc.returncode,
            "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Test run timed out after 60 seconds."}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/scaffold-project", dependencies=[Depends(require_authenticated_client)])
async def scaffold_project(payload: ProjectScaffoldRequest):
    """Scaffold a real project directory inside the MATRIX data workspace."""
    workspace_dir = _validated_project_dir(payload.project_name)
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created_files: List[str] = []
    ptype = payload.project_type.lower()

    if ptype == "python":
        (workspace_dir / "src").mkdir(exist_ok=True)
        (workspace_dir / "tests").mkdir(exist_ok=True)
        (workspace_dir / "src" / "main.py").write_text(
            'def main():\n    print("Hello from MATRIX Generated Project")\n\n'
            'if __name__ == "__main__":\n    main()\n',
            encoding="utf-8",
        )
        (workspace_dir / "tests" / "test_main.py").write_text(
            "def test_example():\n    assert 1 + 1 == 2\n", encoding="utf-8"
        )
        (workspace_dir / "requirements.txt").write_text(
            "pytest>=8.0.0\n", encoding="utf-8"
        )
        (workspace_dir / "README.md").write_text(
            f"# {payload.project_name}\n\n{payload.description}\n", encoding="utf-8"
        )
        created_files = ["src/main.py", "tests/test_main.py", "requirements.txt", "README.md"]

    elif ptype in ("typescript", "javascript"):
        (workspace_dir / "src").mkdir(exist_ok=True)
        (workspace_dir / "package.json").write_text(
            '{\n  "name": "%s",\n  "version": "1.0.0",\n  "type": "module"\n}\n'
            % payload.project_name,
            encoding="utf-8",
        )
        (workspace_dir / "src" / "index.ts").write_text(
            'console.log("Hello from MATRIX TypeScript Project");\n', encoding="utf-8"
        )
        created_files = ["package.json", "src/index.ts"]

    elif ptype == "android":
        (workspace_dir / "app" / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        (workspace_dir / "build.gradle.kts").write_text(
            "// Top-level build file\nplugins {\n    alias(libs.plugins.android.application) apply false\n}\n",
            encoding="utf-8",
        )
        created_files = ["build.gradle.kts", "app/src/main/java/"]

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported project type: {ptype}")

    return {
        "status": "CREATED",
        "project_name": payload.project_name,
        "project_type": ptype,
        "path": str(workspace_dir),
        "files_created": created_files,
    }


@router.get("/export-zip/{project_name}", dependencies=[Depends(require_authenticated_client)])
async def export_zip(project_name: str):
    """Archive and export a previously scaffolded project folder to ZIP format."""
    source_dir = _validated_project_dir(project_name)
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    export_dir = settings.cache_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    archive_path = shutil.make_archive(str(export_dir / project_name), "zip", str(source_dir))

    return {
        "status": "EXPORTED",
        "project_name": project_name,
        "zip_file": archive_path,
        "size_bytes": Path(archive_path).stat().st_size,
    }
