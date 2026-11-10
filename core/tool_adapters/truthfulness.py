"""Truthfulness checks for MATRIX tool adapters.

A ``AdapterExecutionResult(success=True, data={...})`` whose payload is built entirely from
literal constants cannot have come from a device, a network response, or the filesystem.
It is a fabricated result, which MATRIX forbids: adapters must either do real work or
return an explicit ``success=False`` via :func:`unimplemented_result`.

``scan_directory`` returns such sites so CI can block new ones.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

ADAPTER_DIR = Path(__file__).resolve().parent


class Finding(NamedTuple):
    filename: str
    line: int
    detail: str


# Sites reviewed and accepted because the payload is a genuine static catalogue rather
# than a claimed execution result. Keep this empty unless a reviewer has verified it.
REVIEWED_STATIC: set[Tuple[str, int]] = set()


def _is_constant(node: ast.AST) -> bool:
    """True when the expression contains no runtime data (names, calls, attributes)."""
    for child in ast.walk(node):
        if isinstance(child, (ast.Name, ast.Call, ast.Attribute, ast.Subscript)):
            return False
    return True


def _call_name(node: ast.Call) -> str:
    func = node.func
    return func.id if isinstance(func, ast.Name) else getattr(func, "attr", "")


def _keyword(node: ast.Call, key: str) -> Optional[ast.AST]:
    for kw in node.keywords:
        if kw.arg == key:
            return kw.value
    return None


def scan_file(path: Path) -> List[Finding]:
    """Return every fabricated or unsubstantiated success claim in one adapter module."""
    findings: List[Finding] = []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        return [Finding(path.name, exc.lineno or 0, f"file does not parse: {exc.msg}")]

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or _call_name(node) != "AdapterExecutionResult":
            continue

        success = _keyword(node, "success")
        if not (isinstance(success, ast.Constant) and success.value is True):
            continue

        if (path.name, node.lineno) in REVIEWED_STATIC:
            continue

        data = _keyword(node, "data")
        if data is not None and _is_constant(data):
            findings.append(
                Finding(
                    path.name,
                    node.lineno,
                    "success=True with a fully literal data payload "
                    "(cannot be real device/network/filesystem data)",
                )
            )
    return findings


def scan_directory(directory: Path = ADAPTER_DIR) -> List[Finding]:
    """Scan every adapter module in ``directory`` (skipping helper modules)."""
    findings: List[Finding] = []
    for path in sorted(directory.glob("*.py")):
        if path.name in {"__init__.py", "base_adapter.py", "manager.py", "truthfulness.py"}:
            continue
        findings.extend(scan_file(path))
    return findings
