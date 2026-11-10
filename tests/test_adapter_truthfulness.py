"""Adapter truthfulness regression tests (audit milestone 6).

Guards the rule that no adapter may report success with a fabricated payload, and that
the Android bridge reports a missing adb/device instead of inventing data.
"""
from __future__ import annotations

import pytest

from config.settings import settings
from core.tool_adapters.base_adapter import unimplemented_result
from core.tool_adapters.browser_use_adapter import BrowserUseAdapter
from core.tool_adapters.mobile_mcp_adapter import MobileMcpAdapter
from core.tool_adapters.truthfulness import ADAPTER_DIR, scan_directory, scan_file


def test_no_adapter_returns_a_fabricated_success_payload():
    findings = scan_directory(ADAPTER_DIR)
    assert findings == [], "\n".join(
        f"{f.filename}:{f.line} {f.detail}" for f in findings
    )


def test_scanner_detects_a_fabricated_payload():
    """The scanner itself must actually catch the pattern it forbids."""
    scratch = settings.data_dir / "test_workspace" / "truthfulness"
    scratch.mkdir(parents=True, exist_ok=True)
    sample = scratch / "fake_adapter.py"
    sample.write_text(
        "def execute(self):\n"
        "    return AdapterExecutionResult(success=True, adapter_id='x', operation='y',\n"
        "                                  data={'cves': [], 'status': 'CLEAN'})\n",
        encoding="utf-8",
    )
    findings = scan_file(sample)
    assert len(findings) == 1
    assert "literal data" in findings[0].detail


def test_unimplemented_result_is_an_explicit_failure():
    result = unimplemented_result("adapter_test", "do_thing", "no backend", 2.5)
    assert result.success is False
    assert result.error.startswith("NOT IMPLEMENTED")
    assert result.verification["implemented"] is False
    assert result.execution_time_ms == 2.5
    assert result.data is None


@pytest.mark.asyncio
async def test_mobile_adapter_fails_without_adb(monkeypatch):
    adapter = MobileMcpAdapter()
    monkeypatch.setattr(MobileMcpAdapter, "_adb_path", lambda self: None)

    for operation in ("check_adb_devices", "list_packages", "inspect_android_layout"):
        result = await adapter.execute(operation, {})
        assert result.success is False, f"{operation} must not succeed without adb"
        assert "adb" in (result.error or "").lower()


@pytest.mark.asyncio
async def test_mobile_adapter_fails_without_a_device(monkeypatch):
    adapter = MobileMcpAdapter()
    monkeypatch.setattr(MobileMcpAdapter, "_adb_path", lambda self: "adb")
    monkeypatch.setattr(MobileMcpAdapter, "_online_devices", lambda self, adb: [])

    result = await adapter.execute("list_packages", {})
    assert result.success is False
    assert "no online android device" in (result.error or "").lower()

    check = await adapter.execute("check_adb_devices", {})
    assert check.success is True
    assert check.data["device_count"] == 0
    assert "mock_companion_ready" not in check.data


@pytest.mark.asyncio
async def test_browser_adapter_reports_empty_search_instead_of_inventing_results(monkeypatch):
    """A blocked/changed search page must not produce a fabricated result."""
    class _Response:
        status_code = 202
        text = "<html><body>no results</body></html>"

    class _Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, *args, **kwargs):
            return _Response()

    import core.tool_adapters.browser_use_adapter as browser_module

    monkeypatch.setattr(browser_module.httpx, "AsyncClient", _Client)

    adapter = BrowserUseAdapter()
    result = await adapter.execute("search_web", {"query": "matrix ai", "max_results": 3})
    assert result.success is False
    assert "no search results" in (result.error or "").lower()
    assert result.data is None
