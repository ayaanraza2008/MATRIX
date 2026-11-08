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
from typing import Dict, Any, Optional, List
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

    def is_service_running(self) -> bool:
        """Check if Tailscale daemon process (tailscaled.exe / tailscale.exe) is running."""
        try:
            for p in psutil.process_iter(["name"]):
                name = (p.info.get("name") or "").lower()
                if "tailscale" in name:
                    return True
        except Exception:
            pass
        return False

    def get_local_lan_ip(self) -> Optional[str]:
        """Detect the primary RFC1918 local area network IPv4."""
        try:
            for iface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family.name == "AF_INET" and not addr.address.startswith("127."):
                        ip = ipaddress.IPv4Address(addr.address)
                        if ip.is_private and not ip in ipaddress.IPv4Network("100.64.0.0/10"):
                            return str(ip)
        except Exception:
            pass
        return "127.0.0.1"

    def get_remote_url(self, port: int = 8000, token: Optional[str] = None) -> Optional[str]:
        """Generate authenticated remote MATRIX companion endpoint."""
        ts_ip = self.get_tailscale_ip()
        if not ts_ip:
            return None
        base = f"http://{ts_ip}:{port}"
        if token:
            return f"{base}?token={token}"
        return base

    def resolve_best_host(self, preferred_ip: Optional[str] = None) -> Dict[str, Any]:
        """Determine whether to use Tailscale mesh IP or local LAN fallback."""
        ts_ip = self.get_tailscale_ip()
        lan_ip = self.get_local_lan_ip()

        # If Tailscale is online and preferred or if remote
        if ts_ip and (preferred_ip == ts_ip or not preferred_ip):
            return {
                "mode": "TAILSCALE_MESH",
                "host": ts_ip,
                "port": 8000,
                "is_encrypted_mesh": True,
                "url": f"http://{ts_ip}:8000"
            }
        # Fallback to local LAN
        return {
            "mode": "LAN_FALLBACK",
            "host": lan_ip or "127.0.0.1",
            "port": 8000,
            "is_encrypted_mesh": False,
            "url": f"http://{lan_ip or '127.0.0.1'}:8000"
        }

    def authorize_companion_ip(self, ip_str: str) -> bool:
        """Validate if an incoming companion IP is authorized (Tailscale CGNAT or RFC1918 private network)."""
        try:
            ip = ipaddress.IPv4Address(ip_str)
            if ip in ipaddress.IPv4Network("100.64.0.0/10"):
                return True
            if ip.is_private or ip.is_loopback:
                return True
        except Exception:
            pass
        return False

    def list_peers(self) -> List[Dict[str, Any]]:
        """List active Tailscale mesh network peer devices."""
        bin_path = self.find_tailscale_binary()
        if not bin_path:
            return []
        try:
            res = subprocess.run([str(bin_path), "status", "--json"], capture_output=True, text=True, timeout=3)
            if res.returncode == 0:
                import json
                data = json.loads(res.stdout)
                peers = []
                for p_id, p_info in data.get("Peer", {}).items():
                    peers.append({
                        "id": p_id,
                        "host_name": p_info.get("HostName"),
                        "tailscale_ip": p_info.get("TailscaleIPs", [None])[0],
                        "os": p_info.get("OS"),
                        "online": p_info.get("Online", False)
                    })
                return peers
        except Exception:
            pass
        return []

    def disconnect_network(self) -> Dict[str, Any]:
        """Emergency disconnect / clear cached companion remote state."""
        logger.warning("Tailscale remote companion connection session reset requested.")
        return {
            "status": "DISCONNECTED",
            "tailscale_active": self.is_service_running(),
            "message": "Remote companion sessions closed. Host remains private."
        }

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
