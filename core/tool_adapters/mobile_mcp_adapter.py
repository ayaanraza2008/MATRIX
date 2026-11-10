"""MATRIX Mobile & Android MCP Adapter.
Integrates capabilities from mobile-next/mobile-mcp and garagehq/nightcrawler.
Provides real ADB device detection, package queries, and Android UI inspection.

Every operation talks to a live device through ``adb``. When no device is attached or
``adb`` is missing the adapter reports an explicit failure instead of inventing a
device, a package list, or a view hierarchy.
"""
from typing import Dict, Any, List, Optional
import time
import shutil
import subprocess
import xml.etree.ElementTree as ET
from core.tool_adapters.base_adapter import (
    BaseAdapter,
    AdapterExecutionResult,
    unimplemented_result,
)

COMPANION_PACKAGE = "com.matrix.ai"


class MobileMcpAdapter(BaseAdapter):
    """Adapter for Android device interaction, Mobile MCP tools, and ADB bridge."""

    def __init__(self):
        super().__init__(
            adapter_id="adapter_mobile_mcp",
            name="Mobile MCP Android Bridge",
            description="Android device management, ADB inspection, and mobile automation bridge.",
            source_repo="mobile-next/mobile-mcp",
            category="Mobile & Android",
            version="1.1.0"
        )

    @property
    def supported_operations(self) -> List[str]:
        return ["check_adb_devices", "list_packages", "inspect_android_layout"]

    @property
    def input_schema(self) -> Dict[str, Any]:
        return {
            "check_adb_devices": {},
            "list_packages": {"filter_str": "string"},
            "inspect_android_layout": {"device_id": "string"}
        }

    @property
    def output_schema(self) -> Dict[str, Any]:
        return {
            "check_adb_devices": {"devices": "array", "adb_installed": "boolean"},
            "list_packages": {"packages": "array"},
            "inspect_android_layout": {"views": "array"}
        }

    @property
    def permission_requirements(self) -> List[str]:
        return ["adb_access"]

    @property
    def resource_requirements(self) -> Dict[str, Any]:
        return {"ram_mb": 150, "cpu_threads": 1, "requires_gpu": False, "supports_avx2": True}

    # ---- ADB helpers -------------------------------------------------

    def _adb_path(self) -> Optional[str]:
        return shutil.which("adb")

    def _run_adb(self, adb: str, *args: str, timeout: int = 8) -> subprocess.CompletedProcess:
        return subprocess.run(
            [adb, *args], capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace"
        )

    def _online_devices(self, adb: str) -> List[Dict[str, str]]:
        devices: List[Dict[str, str]] = []
        try:
            result = self._run_adb(adb, "devices")
        except (subprocess.TimeoutExpired, OSError):
            return devices
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append({"device_id": parts[0], "status": "online"})
        return devices

    @staticmethod
    def _pick_device(devices: List[Dict[str, str]], requested: Optional[str]) -> Optional[str]:
        if requested:
            return requested if any(d["device_id"] == requested for d in devices) else None
        return devices[0]["device_id"] if devices else None

    # ---- execution ---------------------------------------------------

    async def execute(self, operation: str, parameters: Dict[str, Any]) -> AdapterExecutionResult:
        start_time = time.perf_counter()
        op = operation.lower().strip()
        adb = self._adb_path()

        def elapsed() -> float:
            return round((time.perf_counter() - start_time) * 1000, 2)

        try:
            if op == "check_adb_devices":
                if not adb:
                    return unimplemented_result(
                        self.adapter_id,
                        operation,
                        "adb is not installed or not on PATH (install Android platform-tools)",
                        elapsed(),
                    )

                devices = self._online_devices(adb)
                companion_installed: Optional[bool] = None
                if devices:
                    try:
                        pkgs = self._run_adb(
                            adb, "-s", devices[0]["device_id"], "shell", "pm", "list", "packages", COMPANION_PACKAGE
                        )
                        companion_installed = COMPANION_PACKAGE in (pkgs.stdout or "")
                    except (subprocess.TimeoutExpired, OSError):
                        companion_installed = None

                return AdapterExecutionResult(
                    success=True,
                    adapter_id=self.adapter_id,
                    operation=operation,
                    data={
                        "adb_installed": True,
                        "adb_path": adb,
                        "devices": devices,
                        "device_count": len(devices),
                        "companion_installed": companion_installed,
                    },
                    verification={"adb_queried": True},
                    execution_time_ms=elapsed(),
                )

            if op in ("list_packages", "inspect_android_layout"):
                if not adb:
                    return unimplemented_result(
                        self.adapter_id, operation, "adb is not installed or not on PATH", elapsed()
                    )

                devices = self._online_devices(adb)
                serial = self._pick_device(devices, parameters.get("device_id"))
                if not serial:
                    return unimplemented_result(
                        self.adapter_id,
                        operation,
                        "no online Android device found (connect a phone with USB debugging enabled)",
                        elapsed(),
                    )

                if op == "list_packages":
                    filter_str = (parameters.get("filter_str") or "").strip()
                    result = self._run_adb(adb, "-s", serial, "shell", "pm", "list", "packages")
                    if result.returncode != 0:
                        return unimplemented_result(
                            self.adapter_id,
                            operation,
                            f"'adb shell pm list packages' failed: {(result.stderr or '').strip()[:200]}",
                            elapsed(),
                        )
                    packages = [
                        line.replace("package:", "").strip()
                        for line in (result.stdout or "").splitlines()
                        if line.startswith("package:")
                    ]
                    if filter_str:
                        packages = [p for p in packages if filter_str.lower() in p.lower()]

                    return AdapterExecutionResult(
                        success=True,
                        adapter_id=self.adapter_id,
                        operation=operation,
                        data={"device_id": serial, "packages": packages, "count": len(packages)},
                        verification={"package_list_read": True},
                        execution_time_ms=elapsed(),
                    )

                # inspect_android_layout
                dump = self._run_adb(
                    adb, "-s", serial, "shell", "uiautomator", "dump", "/sdcard/matrix_window.xml", timeout=20
                )
                if dump.returncode != 0:
                    return unimplemented_result(
                        self.adapter_id,
                        operation,
                        f"uiautomator dump failed: {(dump.stderr or '').strip()[:200]}",
                        elapsed(),
                    )
                xml_result = self._run_adb(adb, "-s", serial, "shell", "cat", "/sdcard/matrix_window.xml", timeout=20)
                if xml_result.returncode != 0 or "<hierarchy" not in (xml_result.stdout or ""):
                    return unimplemented_result(
                        self.adapter_id,
                        operation,
                        "could not read the UI hierarchy dump from the device",
                        elapsed(),
                    )

                root = ET.fromstring(xml_result.stdout)
                views = []
                for node in root.iter("node"):
                    views.append(
                        {
                            "class": node.get("class", ""),
                            "text": node.get("text", ""),
                            "resource_id": node.get("resource-id", ""),
                            "bounds": node.get("bounds", ""),
                            "clickable": node.get("clickable") == "true",
                        }
                    )

                return AdapterExecutionResult(
                    success=True,
                    adapter_id=self.adapter_id,
                    operation=operation,
                    data={"device_id": serial, "views": views, "count": len(views)},
                    verification={"ui_hierarchy_parsed": True},
                    execution_time_ms=elapsed(),
                )

            return AdapterExecutionResult(
                success=False,
                adapter_id=self.adapter_id,
                operation=operation,
                error=f"Unsupported operation '{operation}'. Supported: {self.supported_operations}",
                execution_time_ms=elapsed(),
            )

        except (subprocess.TimeoutExpired, OSError) as exc:
            return unimplemented_result(
                self.adapter_id, operation, f"adb call failed: {exc}", elapsed()
            )
        except ET.ParseError as exc:
            return unimplemented_result(
                self.adapter_id, operation, f"UI hierarchy XML could not be parsed: {exc}", elapsed()
            )
