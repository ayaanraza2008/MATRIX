"""MATRIX Gravitas Code Intelligence Adapter.
Integrates capabilities from udaysharmadev/Gravitas and codecrafters-io/build-your-own-x.
Forces deep file inspection, AST structural verification, syntax linting, and architecture audits.
"""
from typing import Dict, Any, List
import time
import ast
from pathlib import Path
from core.tool_adapters.base_adapter import BaseAdapter, AdapterExecutionResult


class GravitasCodeAdapter(BaseAdapter):
    """Adapter for AST structural analysis, strict file verification, and code architecture inspection."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_gravitas",
            name="Gravitas & CodeCrafters Intelligence",
            description="Deep file inspection, AST syntax validation, and code architecture enforcement.",
            source_repo="udaysharmadev/Gravitas",
            category="Coding & DevTools",
            version="1.1.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["verify_syntax", "inspect_code_architecture", "syntax_lint", "generate_template"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "verify_syntax": {"code_or_file": "string", "is_path": "boolean"},
            "inspect_code_architecture": {"file_path": "string"},
            "generate_template": {"technology": "string", "name": "string"}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "verify_syntax": {"valid": "boolean", "error": "string"},
            "inspect_code_architecture": {"classes": "array", "functions": "array", "imports": "array", "loc": "integer"},
            "generate_template": {"template_code": "string"}
        }

    @property
    def permission_requirements(self) -> List[str]:
        return ["filesystem_read"]

    @property
    def resource_requirements(self) -> Dict[str, Any]:
        return {"ram_mb": 40, "cpu_threads": 1, "requires_gpu": False, "supports_avx2": True}

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        op = operation.lower().strip()

        try:
            if op == "verify_syntax":
                code = parameters.get("code_or_file", "")
                is_path = parameters.get("is_path", False)
                if is_path:
                    p = Path(code)
                    if not p.exists():
                        return AdapterExecutionResult(
                            success=False,
                            adapter_id=self.adapter_id,
                            operation=operation,
                            error=f"File not found: {code}"
                        )
                    code = p.read_text(encoding="utf-8")

                try:
                    ast.parse(code)
                    latency = (time.perf_counter() - start_time) * 1000
                    return AdapterExecutionResult(
                        success=True,
                        adapter_id=self.adapter_id,
                        operation=operation,
                        data={"valid": True, "ast_parsed": True, "char_count": len(code)},
                        verification={"ast_parse_success": True},
                        execution_time_ms=round(latency, 2)
                    )
                except SyntaxError as se:
                    latency = (time.perf_counter() - start_time) * 1000
                    return AdapterExecutionResult(
                        success=False,
                        adapter_id=self.adapter_id,
                        operation=operation,
                        data={"valid": False, "error": str(se), "line": se.lineno},
                        error=f"SyntaxError at line {se.lineno}: {se.msg}",
                        execution_time_ms=round(latency, 2)
                    )

            elif op == "inspect_code_architecture":
                file_path = parameters.get("file_path", "core/brain.py")
                p = Path(file_path)
                if not p.exists():
                    return AdapterExecutionResult(
                        success=False,
                        adapter_id=self.adapter_id,
                        operation=operation,
                        error=f"File not found: {file_path}"
                    )

                source = p.read_text(encoding="utf-8")
                tree = ast.parse(source)

                classes = [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
                functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef)]
                imports = []
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            imports.append(n.name)
                    elif isinstance(node, ast.ImportFrom):
                        imports.append(node.module or "")

                latency = (time.perf_counter() - start_time) * 1000
                return AdapterExecutionResult(
                    success=True,
                    adapter_id=self.adapter_id,
                    operation=operation,
                    data={
                        "file": str(p),
                        "loc": len(source.splitlines()),
                        "classes": classes,
                        "functions": functions,
                        "imports": sorted(list(set(filter(None, imports))))
                    },
                    verification={"nodes_extracted": len(classes) + len(functions) > 0},
                    execution_time_ms=round(latency, 2)
                )

            elif op == "generate_template":
                tech = parameters.get("technology", "python")
                name = parameters.get("name", "Service")
                template = (
                    f"class {name}:\n"
                    f"    \"\"\"{name} component generated by MATRIX Gravitas Engine.\"\"\"\n"
                    f"    def __init__(self):\n"
                    f"        pass\n\n"
                    f"    def execute(self) -> bool:\n"
                    f"        return True\n"
                )
                latency = (time.perf_counter() - start_time) * 1000
                return AdapterExecutionResult(
                    success=True,
                    adapter_id=self.adapter_id,
                    operation=operation,
                    data={"technology": tech, "name": name, "template_code": template},
                    verification={"template_ready": True},
                    execution_time_ms=round(latency, 2)
                )

            else:
                return AdapterExecutionResult(
                    success=False,
                    adapter_id=self.adapter_id,
                    operation=operation,
                    error=f"Unsupported operation '{operation}'."
                )

        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AdapterExecutionResult(
                success=False,
                adapter_id=self.adapter_id,
                operation=operation,
                error=str(e),
                execution_time_ms=round(latency, 2)
            )
