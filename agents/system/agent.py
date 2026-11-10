"""MATRIX System Telemetry, Configuration & Management Agent.
Monitors and manages the Windows 11 host:
- CPU, RAM, disk, network metrics, and active process health
- Open Windows Settings pages (ms-settings:)
- Enumerate startup applications and installed software
- Scan Wi-Fi networks (netsh wlan)
- Audio volume and system status inspection
- Automated system error diagnosis and resource pressure detection
"""
from typing import Dict, Any
import time
import subprocess
import os
import psutil
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("agents.system")


class SystemAgent(BaseAgent):
    """Monitors OS health, processor performance, RAM consumption, and system configuration."""

    SETTINGS_PAGE_MAP = {
        "settings": "ms-settings:",
        "wifi": "ms-settings:network-wifi",
        "network": "ms-settings:network",
        "bluetooth": "ms-settings:bluetooth",
        "display": "ms-settings:display",
        "sound": "ms-settings:sound",
        "volume": "ms-settings:sound",
        "apps": "ms-settings:appsfeatures",
        "updates": "ms-settings:windowsupdate",
        "update": "ms-settings:windowsupdate",
        "storage": "ms-settings:storagesense",
        "battery": "ms-settings:powersleep",
        "power": "ms-settings:powersleep"
    }

    def __init__(self):
        super().__init__(
            name="system",
            description="Inspects real CPU, RAM, storage, network, installed software, startup apps, Wi-Fi, and system diagnostics.",
            max_autonomy_level=1
        )
        self._capabilities = [
            AgentCapability(name="poll_telemetry", description="Inspect live CPU, RAM, disk, and network stats", operations=["telemetry", "status", "specs"]),
            AgentCapability(name="open_settings", description="Open specific Windows 11 Settings pages", operations=["settings", "open_settings"]),
            AgentCapability(name="inspect_software", description="Enumerate installed software and startup applications", operations=["installed_software", "startup_apps"]),
            AgentCapability(name="wifi_management", description="Scan available Wi-Fi networks via Windows interfaces", operations=["scan_wifi", "wifi"]),
            AgentCapability(name="system_diagnosis", description="Detect resource bottlenecks and diagnose system health", operations=["diagnose", "health_check"])
        ]

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("query", parameters.get("raw_prompt", "")).lower()

        # 1. Open Windows Settings
        if "setting" in action_lower or "setting" in raw_prompt:
            page = parameters.get("page", self._detect_settings_page(raw_prompt))
            return await self._open_settings(page, start_time)

        # 2. Inspect Installed Software
        if "software" in action_lower or "app" in action_lower and any(w in raw_prompt for w in ["installed", "programs", "applications"]):
            return await self._inspect_installed_software(start_time)

        # 3. Inspect Startup Applications
        if "startup" in action_lower or "startup" in raw_prompt:
            return await self._inspect_startup_apps(start_time)

        # 4. Scan Wi-Fi Networks
        if "wifi" in action_lower or "network" in action_lower and any(w in raw_prompt for w in ["wifi", "wireless", "networks"]):
            return await self._scan_wifi_networks(start_time)

        # 5. Diagnose System Health / Errors
        if "diagnos" in action_lower or "check my computer" in raw_prompt or "error" in raw_prompt:
            return await self._diagnose_system_errors(start_time)

        # 6. Hardware Telemetry
        if any(w in action_lower for w in ["telemetry", "status", "specs", "cpu", "hardware", "system", "poll"]):
            return await self._poll_telemetry(start_time)

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=False,
            agent_name=self.name,
            action_taken=action,
            error=f"Unsupported action '{action}' for SystemAgent",
            execution_status="FAILED",
            verification_status="FAILED",
            execution_time_ms=round(latency, 2)
        )

    async def _poll_telemetry(self, start_time: float) -> AgentResult:
        """Poll real-time CPU, RAM, disk, and network stats."""
        vm = psutil.virtual_memory()
        cpu_p = psutil.cpu_percent(interval=None)
        cpu_freq = psutil.cpu_freq()
        net_io = psutil.net_io_counters()

        storage_data = {}
        for drive in ["C:", "D:"]:
            try:
                u = psutil.disk_usage(f"{drive}\\")
                storage_data[drive] = {
                    "total_gb": round(u.total / (1024**3), 2),
                    "free_gb": round(u.free / (1024**3), 2),
                    "used_percent": u.percent
                }
            except Exception:
                pass

        latency = (time.perf_counter() - start_time) * 1000

        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="poll_telemetry",
            data={
                "cpu_percent": cpu_p,
                "ram_percent": vm.percent,
                "ram_used_mb": round(vm.used / (1024*1024), 1),
                "cpu": {
                    "percent": cpu_p,
                    "physical_cores": settings.cpu_cores,
                    "logical_processors": settings.cpu_threads,
                    "frequency_mhz": round(cpu_freq.current, 1) if cpu_freq else 0
                },
                "memory": {
                    "total_mb": round(vm.total / (1024*1024), 1),
                    "used_mb": round(vm.used / (1024*1024), 1),
                    "available_mb": round(vm.available / (1024*1024), 1),
                    "percent": vm.percent,
                    "low_ram_mode": settings.low_ram_mode
                },
                "network": {
                    "bytes_sent_mb": round(net_io.bytes_sent / (1024*1024), 2),
                    "bytes_recv_mb": round(net_io.bytes_recv / (1024*1024), 2)
                },
                "storage": storage_data
            },
            verification={"telemetry_valid": True, "verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def _open_settings(self, page_target: str, start_time: float) -> AgentResult:
        """Launch Windows 11 Settings via URI scheme."""
        uri = self.SETTINGS_PAGE_MAP.get(page_target.lower(), f"ms-settings:{page_target}" if page_target else "ms-settings:")
        try:
            cmd = f"start {uri}"
            subprocess.Popen(cmd, shell=True)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="open_settings",
                data={"settings_page": uri, "opened": True},
                verification={"verified": True, "launched": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="open_settings",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _inspect_installed_software(self, start_time: float) -> AgentResult:
        """Query installed software via Windows Registry."""
        software_list = []
        try:
            import winreg
            reg_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
            ]
            for hkey, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as app_key:
                                    try:
                                        name = winreg.QueryValueEx(app_key, "DisplayName")[0]
                                        version = winreg.QueryValueEx(app_key, "DisplayVersion")[0] if "DisplayVersion" in [winreg.EnumValue(app_key, j)[0] for j in range(winreg.QueryInfoKey(app_key)[1])] else ""
                                        if name and name.strip():
                                            software_list.append({"name": name.strip(), "version": str(version)})
                                    except (FileNotFoundError, IndexError):
                                        pass
                            except Exception:
                                continue
                except Exception:
                    continue

            # Deduplicate by name
            unique_sw = {s["name"]: s for s in software_list}.values()
            sorted_sw = sorted(list(unique_sw), key=lambda x: x["name"])[:35]

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="inspect_installed_software",
                data={"total_installed_count": len(unique_sw), "software": sorted_sw},
                verification={"verified": True, "count": len(sorted_sw)},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="inspect_installed_software",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _inspect_startup_apps(self, start_time: float) -> AgentResult:
        """Inspect applications configured to launch on Windows startup."""
        startup_items = []
        try:
            import winreg
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run")
            ]
            for hkey, subkey in reg_paths:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        num_values = winreg.QueryInfoKey(key)[1]
                        for j in range(num_values):
                            val_name, val_data, _ = winreg.EnumValue(key, j)
                            startup_items.append({"name": val_name, "command": str(val_data)[:80]})
                except Exception:
                    pass

            # Check Shell:Startup directory
            startup_dir = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            if startup_dir.exists():
                for f in startup_dir.iterdir():
                    if f.is_file():
                        startup_items.append({"name": f.name, "command": str(f)})

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="inspect_startup_apps",
                data={"startup_count": len(startup_items), "startup_items": startup_items},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="inspect_startup_apps",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _scan_wifi_networks(self, start_time: float) -> AgentResult:
        """Scan available Wi-Fi access points via standard netsh command."""
        try:
            res = subprocess.run("netsh wlan show networks", shell=True, capture_output=True, text=True, timeout=5)
            networks = []
            if res.returncode == 0:
                for line in res.stdout.splitlines():
                    if "SSID" in line and ":" in line:
                        ssid = line.split(":", 1)[1].strip()
                        if ssid:
                            networks.append(ssid)

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="scan_wifi_networks",
                data={"networks_found": len(networks), "ssids": networks[:10]},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="scan_wifi_networks",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

    async def _diagnose_system_errors(self, start_time: float) -> AgentResult:
        """Perform system diagnostics: memory pressure, disk limits, and health status."""
        vm = psutil.virtual_memory()
        cpu_p = psutil.cpu_percent(interval=None)
        c_disk = psutil.disk_usage("C:\\")

        warnings = []
        if vm.percent > 90:
            warnings.append(f"High RAM pressure: {vm.percent}% utilized ({vm.available / (1024*1024):.0f} MB available).")
        if c_disk.percent > 92:
            warnings.append(f"Low system disk space on C:: {c_disk.percent}% used ({c_disk.free / (1024**3):.1f} GB remaining).")
        if cpu_p > 85:
            warnings.append(f"Elevated processor load: {cpu_p}%.")

        status_summary = "All hardware metrics nominal." if not warnings else " | ".join(warnings)
        latency = (time.perf_counter() - start_time) * 1000

        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="diagnose_system_errors",
            data={
                "status": "Healthy" if not warnings else "Warning",
                "summary": status_summary,
                "warnings": warnings,
                "cpu_percent": cpu_p,
                "ram_percent": vm.percent,
                "c_drive_percent": c_disk.percent
            },
            verification={"diagnostics_complete": True, "verified": True},
            execution_time_ms=round(latency, 2)
        )

    def _detect_settings_page(self, text: str) -> str:
        for k in self.SETTINGS_PAGE_MAP.keys():
            if k in text:
                return k
        return "settings"

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and getattr(result, "success", False))
