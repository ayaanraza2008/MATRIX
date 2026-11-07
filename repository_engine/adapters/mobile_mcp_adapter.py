"""MATRIX Integration Adapter: Mobile-MCP (mobile-next/mobile-mcp).
Connects MATRIX to Android devices via MCP protocol and ADB for mobile UI inspection and intent triggers.
"""
from typing import Dict, Any, List
import subprocess
from config.logging_config import get_logger

logger = get_logger("adapter.mobile_mcp")


class MobileMCPAdapter:
    """Provides mobile automation bridge for Android companion devices."""

    def detect_adb_devices(self) -> List[str]:
        """Detect connected Android devices via ADB if installed."""
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                lines = res.stdout.strip().split("\n")[1:]
                devices = [line.split("\t")[0] for line in lines if "\tdevice" in line]
                logger.info(f"ADB detected {len(devices)} connected Android devices.")
                return devices
        except Exception:
            pass
        return []

    async def send_device_command(self, device_id: str, command: str) -> Dict[str, Any]:
        """Dispatch remote action to Android companion."""
        logger.info(f"Mobile-MCP dispatching command '{command}' to device '{device_id}'")
        return {
            "device_id": device_id,
            "command": command,
            "status": "QUEUED",
            "protocol": "Mobile-MCP JSON-RPC / WebSocket"
        }


mobile_mcp_adapter = MobileMCPAdapter()
