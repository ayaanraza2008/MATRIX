"""MATRIX Tailscale Private Mesh Network Manager.
Handles automated detection of Tailscale WireGuard mesh networking,
private CGNAT IP discovery (100.64.0.0/10 range), authentication status checks,
and setup guidance for secure remote companion connectivity.
"""
import os
import shutil
import subprocess
import ipaddress
import psutil
from typing import Dict, Any, Optional
from pathlib import Path
from config.logging_config import get_logger

logger = get_logger("core.tailscale")

COMMON_TAILSCALE_PATHS = [
    Path(os.environ.get("ProgramFiles", "C:\\Program Files")) / "Tailscale" / "tailscale.exe",
    Path(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")) / "Tailscale" / "tailscale.exe",
    Path(os.environ.get("LocalAppData", "C:\\Users\\Default\\AppData\\Local")) / "Tailscale" / "tailscale.exe"
]


class TailscaleManager:
    """Manages Tailscale discovery, IP resolution, and connection readiness."""

    def find_tailscale_binary(self) -> Optional[Path]:
        """Locate tailscale CLI binary in PATH or default installation directories."""
        in_path = shutil.which("tailscale")
        if in_path:
            return Path(in_path)
        for p in COMMON_TAILSCALE_PATHS:
            if p.exists() and p.is_file():
                return p
        return None

    def is_installed(self) -> bool:
        return self.find_tailscale_binary() is not None

    def get_tailscale_ip(self) -> Optional[str]:
        """Detect the private 100.64.0.0/10 IPv4 assigned by Tailscale."""
        try:
            tailscale_net = ipaddress.IPv4Network("100.64.0.0/10")
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family.name == "AF_INET":
                        ip = ipaddress.IPv4Address(addr.address)
                        if ip in tailscale_net:
                            return str(ip)
        except Exception:
            pass

        bin_path = self.find_tailscale_binary()
        if bin_path:
            try:
                res = subprocess.run([str(bin_path), "ip", "-4"], capture_output=True, text=True, timeout=2)
                if res.returncode == 0:
                    ip = res.stdout.strip()
                    if ip:
                        return ip
            except Exception:
                pass
        return None

    def get_readiness_status(self) -> Dict[str, Any]:
        """Comprehensive status of Tailscale installation, login status, and IP connectivity."""
        installed = self.is_installed()
        bin_path = str(self.find_tailscale_binary()) if installed else None
        ts_ip = self.get_tailscale_ip()
        is_authenticated = False
        tailnet_name = None

        if installed and bin_path:
            try:
                res = subprocess.run([bin_path, "status"], capture_output=True, text=True, timeout=2.5)
                if res.returncode == 0 and "Logged out" not in res.stdout:
                    is_authenticated = True
                    # Extract tailnet or device line if available
                    for line in res.stdout.splitlines():
                        if "#" in line or "tailscale" in line.lower():
                            tailnet_name = line.strip()
                            break
            except Exception:
                pass

        ready = installed and is_authenticated and (ts_ip is not None)

        return {
            "installed": installed,
            "binary_path": bin_path,
            "authenticated": is_authenticated,
            "tailscale_ip": ts_ip,
            "tailnet": tailnet_name,
            "ready_for_remote_companion": ready,
            "setup_instructions": {
                "step_1": "Download and install Tailscale for Windows from https://tailscale.com/download/windows",
                "step_2": "Open Tailscale from the Windows System Tray and log in with your personal account (Google/GitHub/Apple/Microsoft)",
                "step_3": "Install the Tailscale app on your Android phone from Google Play Store and log in to the same account",
                "step_4": "In MATRIX Mobile Android app, enter Server Host as <tailscale_ip>:8000 for encrypted mobile access away from home"
            } if not ready else None
        }


# Global singleton instance
tailscale_manager = TailscaleManager()
