"""MATRIX Developer Studio API Route.
Provides Python code syntax validation, sandbox execution, test suite runners,
project scaffolding (Python, JS/TS, Android), and project ZIP exports.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import subprocess
import time
import ast
import sys
import shutil
from pathlib import Path
from typing import Optional, List
from config.settings import settings

router = APIRouter(prefix="/developer", tags=["Developer Studio"])


class CodeRunRequest(BaseModel):
    code: str


class TestRunRequest(BaseModel):
    test_file: str = "tests/test_foundation.py"


class ProjectScaffoldRequest(BaseModel):
    project_name: str
    project_type: str = "python"  # 'python', 'typescript', 'android'
    description: Optional[str] = "MATRIX Generated Project"


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
            timeout=8
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
        return {"success": False, "error": "Execution timed out after 8 seconds."}
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
            timeout=30
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


@router.post("/scaffold-project")
async def scaffold_project(payload: ProjectScaffoldRequest):
    """Scaffold a real project directory for Python, TypeScript, or Android in the sandbox."""
    workspace_dir = Path("D:/matrix_data/test_workspace/projects") / payload.project_name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    created_files = []
    ptype = payload.project_type.lower()

    if ptype == "python":
        (workspace_dir / "src").mkdir(exist_ok=True)
        (workspace_dir / "tests").mkdir(exist_ok=True)
        main_py = workspace_dir / "src" / "main.py"
        main_py.write_text('def main():\n    print("Hello from MATRIX Generated Project")\n\nif __name__ == "__main__":\n    main()\n', encoding="utf-8")
        test_py = workspace_dir / "tests" / "test_main.py"
        test_py.write_text('def test_example():\n    assert 1 + 1 == 2\n', encoding="utf-8")
        req_txt = workspace_dir / "requirements.txt"
        req_txt.write_text('pytest>=8.0.0\n', encoding="utf-8")
        readme = workspace_dir / "README.md"
        readme.write_text(f"# {payload.project_name}\n\n{payload.description}\n", encoding="utf-8")
        created_files = ["src/main.py", "tests/test_main.py", "requirements.txt", "README.md"]

    elif ptype in ("typescript", "javascript"):
        (workspace_dir / "src").mkdir(exist_ok=True)
        pkg_json = workspace_dir / "package.json"
        pkg_json.write_text(f'{{\n  "name": "{payload.project_name}",\n  "version": "1.0.0",\n  "type": "module"\n}}\n', encoding="utf-8")
        index_ts = workspace_dir / "src" / "index.ts"
        index_ts.write_text('console.log("Hello from MATRIX TypeScript Project");\n', encoding="utf-8")
        created_files = ["package.json", "src/index.ts"]

    elif ptype == "android":
        (workspace_dir / "app" / "src" / "main" / "java").mkdir(parents=True, exist_ok=True)
        build_gradle = workspace_dir / "build.gradle.kts"
        build_gradle.write_text('// Top-level build file\nplugins {\n    alias(libs.plugins.android.application) apply false\n}\n', encoding="utf-8")
        created_files = ["build.gradle.kts", "app/src/main/java/"]

    return {
        "status": "CREATED",
        "project_name": payload.project_name,
        "project_type": ptype,
        "path": str(workspace_dir),
        "files_created": created_files
    }


@router.get("/export-zip/{project_name}")
async def export_zip(project_name: str):
    """Archive and export a project folder to ZIP format."""
    source_dir = Path("D:/matrix_data/test_workspace/projects") / project_name
    if not source_dir.exists():
        raise HTTPException(status_code=404, detail="Project not found")

    export_dir = Path("D:/matrix_data/cache/exports")
    export_dir.mkdir(parents=True, exist_ok=True)
    archive_base = export_dir / project_name
    archive_path = shutil.make_archive(str(archive_base), 'zip', str(source_dir))

    return {
        "status": "EXPORTED",
        "project_name": project_name,
        "zip_file": archive_path,
        "size_bytes": Path(archive_path).stat().st_size
    }
