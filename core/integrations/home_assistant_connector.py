"""MATRIX Home Assistant IoT Integration Connector.
Real Home Assistant REST API client for smart device telemetry and automation control.
Interacts with local/remote Home Assistant instances via Long-Lived Access Tokens.
"""
from typing import Dict, Any, List, Optional
import os
import json
import time
from pathlib import Path
import httpx

from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.integrations.home_assistant")


class HomeAssistantConnector:
    """Manages real Home Assistant REST API communication, entity inspection, and state changes."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._token_file = self._creds_dir / "hass_token.txt"
        self._url_file = self._creds_dir / "hass_url.txt"
        self._token = os.getenv("HASS_TOKEN", "")
        self._base_url = os.getenv("HASS_URL", "http://homeassistant.local:8123").rstrip("/")
        self._load_credentials()

    def _load_credentials(self):
        if self._token_file.exists():
            try:
                t = self._token_file.read_text(encoding="utf-8").strip()
                if t:
                    self._token = t
            except Exception:
                pass
        if self._url_file.exists():
            try:
                u = self._url_file.read_text(encoding="utf-8").strip().rstrip("/")
                if u:
                    self._base_url = u
            except Exception:
                pass

    def save_credentials(self, base_url: str, token: str):
        self._base_url = base_url.strip().rstrip("/")
        self._token = token.strip()
        self._url_file.write_text(self._base_url, encoding="utf-8")
        self._token_file.write_text(self._token, encoding="utf-8")
        logger.info(f"Home Assistant credentials saved for {self._base_url}")

    def disconnect(self):
        self._token = ""
        if self._token_file.exists():
            self._token_file.unlink()
        logger.info("Home Assistant integration disconnected.")

    def is_configured(self) -> bool:
        return bool(self._token)

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json"
        }

    async def verify_connection(self) -> Dict[str, Any]:
        """Test API connectivity using GET /api/."""
        if not self._token:
            return {
                "connected": False,
                "status": "NOT_CONFIGURED",
                "message": "Home Assistant Long-Lived Access Token is not configured."
            }

        api_url = f"{self._base_url}/api/"
        async with httpx.AsyncClient(timeout=6.0) as client:
            try:
                res = await client.get(api_url, headers=self._get_headers())
                if res.status_code == 200:
                    data = res.json()
                    # Try to fetch version from /api/config if possible
                    version = "unknown"
                    try:
                        cfg_res = await client.get(f"{self._base_url}/api/config", headers=self._get_headers())
                        if cfg_res.status_code == 200:
                            cfg_data = cfg_res.json()
                            version = cfg_data.get("version", "unknown")
                    except Exception:
                        pass

                    return {
                        "connected": True,
                        "status": "CONNECTED",
                        "base_url": self._base_url,
                        "message": data.get("message", "API running"),
                        "ha_version": version
                    }
                return {
                    "connected": False,
                    "status": "ERROR",
                    "status_code": res.status_code,
                    "error": res.text
                }
            except Exception as e:
                return {"connected": False, "status": "ERROR", "error": f"Cannot connect to {self._base_url}: {e}"}

    async def get_states(self) -> Dict[str, Any]:
        """Fetch current states of all devices/entities."""
        if not self._token:
            return {"authenticated": False, "message": "Home Assistant token not configured."}

        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.get(f"{self._base_url}/api/states", headers=self._get_headers())
                if res.status_code == 200:
                    states = res.json()
                    summaries = []
                    for s in states:
                        summaries.append({
                            "entity_id": s.get("entity_id"),
                            "state": s.get("state"),
                            "friendly_name": s.get("attributes", {}).get("friendly_name", s.get("entity_id")),
                            "last_changed": s.get("last_changed")
                        })
                    return {"success": True, "count": len(summaries), "entities": summaries}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def get_entity_state(self, entity_id: str) -> Dict[str, Any]:
        """Fetch specific entity state and attributes."""
        if not self._token:
            return {"authenticated": False, "message": "Home Assistant token not configured."}

        async with httpx.AsyncClient(timeout=6.0) as client:
            try:
                res = await client.get(f"{self._base_url}/api/states/{entity_id}", headers=self._get_headers())
                if res.status_code == 200:
                    return {"success": True, "data": res.json()}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}

    async def call_service(
        self,
        domain: str,
        service: str,
        service_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Call a Home Assistant service (e.g. light/turn_on, switch/toggle).
        Sensitive actions (lock, alarm, cover) require Level 4 supervisor confirmation.
        """
        if not self._token:
            return {"authenticated": False, "message": "Home Assistant token not configured."}

        # Sensitivity check
        sensitive_domains = {"lock", "alarm_control_panel", "cover"}
        if domain in sensitive_domains:
            from security.permissions.manager import permission_manager
            perm = permission_manager.check_permission(f"hass.{domain}.{service}")
            if not perm.allowed:
                return {
                    "success": False,
                    "requires_confirmation": True,
                    "confirmation_token": perm.confirmation_token,
                    "message": f"Service call '{domain}.{service}' requires supervisor confirmation."
                }

        url = f"{self._base_url}/api/services/{domain}/{service}"
        payload = service_data or {}
        async with httpx.AsyncClient(timeout=8.0) as client:
            try:
                res = await client.post(url, headers=self._get_headers(), json=payload)
                if res.status_code == 200:
                    return {"success": True, "domain": domain, "service": service, "result": res.json()}
                return {"success": False, "status_code": res.status_code, "error": res.text}
            except Exception as e:
                return {"success": False, "error": str(e)}


home_assistant_connector = HomeAssistantConnector()
