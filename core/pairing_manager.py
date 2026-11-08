"""MATRIX Pairing Manager & LAN/Tailscale Network Utilities.
Manages cryptographic pairing tokens, TTL expiration, consumption tracking, and LAN/Tailscale IP detection
for seamless synchronization between the Windows 11 PC host and mobile/remote companion devices.
"""
import socket
import time
import uuid
import threading
from typing import Dict, Any, Optional, Tuple, List


def get_lan_ip() -> str:
    """Discover the host machine's primary local area network IPv4 address.
    Falls back to 127.0.0.1 if disconnected from all network interfaces.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to public DNS address without sending packets to query default gateway routing
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    finally:
        s.close()

    try:
        host_name = socket.gethostname()
        for ip in socket.gethostbyname_ex(host_name)[2]:
            if not ip.startswith("127."):
                return ip
    except Exception:
        pass

    return "127.0.0.1"


def get_tailscale_ip() -> Optional[str]:
    """Discover host IPv4 address on private Tailscale mesh network (100.64.0.0/10 CGNAT range).
    Returns None if Tailscale interface is not active on this host.
    """
    try:
        import ipaddress
        import psutil
        tailscale_net = ipaddress.IPv4Network("100.64.0.0/10")
        for iface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family.name == "AF_INET":
                    ip = ipaddress.IPv4Address(addr.address)
                    if ip in tailscale_net:
                        return str(ip)
    except Exception:
        pass

    try:
        import subprocess
        res = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=1.5)
        if res.returncode == 0:
            ip = res.stdout.strip()
            if ip:
                return ip
    except Exception:
        pass

    return None


class PairingTokenRecord:
    def __init__(self, token: str, ttl_seconds: int = 300):
        self.token = token
        self.created_at = time.time()
        self.ttl_seconds = ttl_seconds
        self.is_consumed = False
        self.consumed_by: Optional[str] = None
        self.consumed_at: Optional[float] = None

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds

    def to_dict(self) -> Dict[str, Any]:
        remaining = max(0.0, self.ttl_seconds - (time.time() - self.created_at))
        return {
            "token": self.token,
            "created_at": self.created_at,
            "ttl_seconds": self.ttl_seconds,
            "expires_in_seconds": round(remaining, 1),
            "is_consumed": self.is_consumed,
            "is_expired": self.is_expired,
            "consumed_by": self.consumed_by
        }


class PairingManager:
    """Singleton pairing manager tracking one-time authorization tokens."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(PairingManager, cls).__new__(cls)
                cls._instance._registry: Dict[str, PairingTokenRecord] = {}
                cls._instance._reg_lock = threading.Lock()
            return cls._instance

    def create_token(self, ttl_seconds: int = 300, port: int = 8000) -> Dict[str, Any]:
        """Generate and register a new pairing token and formatted QR protocol URI with LAN/Tailscale IP."""
        token_id = f"mtx_pair_{uuid.uuid4().hex[:16]}"
        record = PairingTokenRecord(token=token_id, ttl_seconds=ttl_seconds)

        with self._reg_lock:
            self._registry[token_id] = record
            self._cleanup_expired_locked()

        lan_ip = get_lan_ip()
        ts_ip = get_tailscale_ip()
        host_endpoint = f"{lan_ip}:{port}"
        qr_uri = f"matrix://pair?token={token_id}&host={host_endpoint}"
        ts_endpoint = f"{ts_ip}:{port}" if ts_ip else None
        ts_qr_uri = f"matrix://pair?token={token_id}&host={ts_endpoint}" if ts_endpoint else None

        return {
            "pairing_token": token_id,
            "qr_protocol": qr_uri,
            "host": host_endpoint,
            "lan_ip": lan_ip,
            "tailscale_ip": ts_ip,
            "tailscale_host": ts_endpoint,
            "tailscale_qr_protocol": ts_qr_uri,
            "port": port,
            "expires_in_seconds": ttl_seconds,
            "created_at": record.created_at,
            "remote_compatible": bool(ts_ip)
        }

    def validate_and_consume(self, token: str, device_id: Optional[str] = None) -> Tuple[bool, str]:
        """Validate token format, existence, expiry, and consumption status.
        Marks token consumed if valid.
        """
        if not token or not isinstance(token, str) or not token.startswith("mtx_pair_"):
            return False, "Invalid pairing token format. Tokens must begin with 'mtx_pair_'."

        with self._reg_lock:
            record = self._registry.get(token)
            if not record:
                return False, "Pairing token not recognized or already discarded."

            if record.is_consumed:
                return False, f"Pairing token has already been consumed by device '{record.consumed_by}'."

            if record.is_expired:
                return False, f"Pairing token expired {round(time.time() - record.created_at - record.ttl_seconds, 1)}s ago."

            record.is_consumed = True
            record.consumed_by = device_id or "unknown"
            record.consumed_at = time.time()
            return True, "Token validated and consumed successfully."

    def is_valid(self, token: str) -> bool:
        with self._reg_lock:
            record = self._registry.get(token)
            if not record:
                return False
            return not record.is_consumed and not record.is_expired

    def list_active_tokens(self) -> List[Dict[str, Any]]:
        with self._reg_lock:
            self._cleanup_expired_locked()
            return [r.to_dict() for r in self._registry.values() if not r.is_consumed and not r.is_expired]

    def _cleanup_expired_locked(self):
        now = time.time()
        # Clean records older than 2x TTL to keep registry compact
        to_delete = [
            k for k, r in self._registry.items()
            if (now - r.created_at) > (r.ttl_seconds * 2)
        ]
        for k in to_delete:
            del self._registry[k]

    def clear(self):
        with self._reg_lock:
            self._registry.clear()


# Global module singleton
pairing_manager = PairingManager()
