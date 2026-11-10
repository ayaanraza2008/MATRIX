"""CLI wrapper around :mod:`core.tool_adapters.truthfulness`.

Fails when an adapter returns success with a fabricated (fully literal) payload.

    python scripts/audit_adapter_truthfulness.py
"""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.tool_adapters.truthfulness import ADAPTER_DIR, scan_directory  # noqa: E402


def main() -> int:
    findings = scan_directory(ADAPTER_DIR)
    if not findings:
        print(f"OK: no fabricated success payloads in {ADAPTER_DIR.name}/")
        return 0

    print(f"FOUND {len(findings)} fabricated success payload(s):")
    for finding in findings:
        print(f"  {finding.filename}:{finding.line}  {finding.detail}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
