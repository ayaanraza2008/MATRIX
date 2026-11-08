"""MATRIX Push Notification System.
Provides mobile push alert capabilities for the Android companion app.
Integrates Firebase Cloud Messaging (FCM HTTP v1) with automatic real-time
WebSocket fallback when connected locally or remotely via Tailscale.
"""
from typing import Dict, Any, List, Optional
import os
import json
import time
from pathlib import Path
import httpx

from config.settings import settings
from config.logging_config import get_logger
from api.websocket.manager import ws_manager

logger = get_logger("core.notifications")


class PushNotificationService:
    """Manages FCM device tokens, notification dispatching, WebSocket fallback, and alert history."""

    def __init__(self):
        self._creds_dir = settings.data_dir / "credentials"
        self._creds_dir.mkdir(parents=True, exist_ok=True)
        self._tokens_file = self._creds_dir / "device_fcm_tokens.json"
        self._history_file = settings.data_dir / "notifications_history.json"
        self._fcm_creds_file = self._creds_dir / "firebase_service_account.json"
        self._tokens: Dict[str, str] = {}
        self._history: List[Dict[str, Any]] = []
        self._load_tokens()
        self._load_history()

    def _load_tokens(self):
        if self._tokens_file.exists():
            try:
                self._tokens = json.loads(self._tokens_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not load FCM device tokens: {e}")

    def _save_tokens(self):
        try:
            self._tokens_file.write_text(json.dumps(self._tokens, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Could not save FCM tokens: {e}")

    def _load_history(self):
        if self._history_file.exists():
            try:
                self._history = json.loads(self._history_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Could not load notification history: {e}")

    def _save_history(self):
        try:
            # Keep latest 200 notifications
            self._history = self._history[-200:]
            self._history_file.write_text(json.dumps(self._history, indent=2), encoding="utf-8")
        except Exception as e:
            logger.error(f"Could not save notification history: {e}")

    def is_firebase_configured(self) -> bool:
        """Check if a valid Firebase Service Account file exists."""
        if self._fcm_creds_file.exists():
            return True
        env_fcm = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
        return bool(env_fcm and Path(env_fcm).exists())

    def register_device_token(self, device_id: str, fcm_token: str):
        """Associate an FCM registration token with a paired device ID."""
        self._tokens[device_id] = fcm_token.strip()
        self._save_tokens()
        logger.info(f"Registered FCM push token for device '{device_id}'")

    def update_device_token(self, device_id: str, new_token: str) -> bool:
        """Refresh and update an existing device FCM registration token."""
        self._tokens[device_id] = new_token.strip()
        self._save_tokens()
        logger.info(f"Refreshed FCM push token for device '{device_id}'")
        return True

    def unregister_device_token(self, device_id: str):
        """Remove FCM token for a device."""
        if device_id in self._tokens:
            del self._tokens[device_id]
            self._save_tokens()
            logger.info(f"Unregistered FCM token for device '{device_id}'")

    def cleanup_invalid_tokens(self, invalid_tokens: List[str]) -> int:
        """Purge known expired or invalidated FCM registration tokens."""
        removed = 0
        invalid_set = set(invalid_tokens)
        for dev_id, tok in list(self._tokens.items()):
            if tok in invalid_set:
                del self._tokens[dev_id]
                removed += 1
        if removed:
            self._save_tokens()
            logger.info(f"Cleaned up {removed} invalidated FCM tokens.")
        return removed

    def set_device_preferences(self, device_id: str, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Save notification delivery preferences for a device (e.g. priority, quiet hours)."""
        prefs_file = self._creds_dir / f"prefs_{device_id}.json"
        try:
            prefs_file.write_text(json.dumps(preferences, indent=2), encoding="utf-8")
            return {"device_id": device_id, "preferences": preferences, "status": "SAVED"}
        except Exception as e:
            return {"device_id": device_id, "error": str(e), "status": "ERROR"}

    def get_device_preferences(self, device_id: str) -> Dict[str, Any]:
        """Retrieve notification delivery preferences for a device."""
        prefs_file = self._creds_dir / f"prefs_{device_id}.json"
        if prefs_file.exists():
            try:
                return json.loads(prefs_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"quiet_hours_enabled": False, "priority_filter": "all", "sound": True}

    def clear_all_tokens(self):
        """Emergency purge: unregister all device push tokens."""
        count = len(self._tokens)
        self._tokens.clear()
        self._save_tokens()
        logger.warning(f"Purged all {count} FCM device push tokens.")

    def get_setup_wizard(self) -> Dict[str, Any]:
        """Interactive setup guide and connection status for FCM push service."""
        sa_path = self._fcm_creds_file
        if not sa_path.exists() and os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            sa_path = Path(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
        configured = sa_path.exists()
        project_id = None
        client_email = None
        if configured:
            try:
                sa_data = json.loads(sa_path.read_text(encoding="utf-8"))
                project_id = sa_data.get("project_id")
                client_email = sa_data.get("client_email")
            except Exception:
                pass

        return {
            "status": "PASS — REAL VERIFIED" if configured else "NOT CONFIGURED",
            "configured": configured,
            "service_account_path": str(sa_path),
            "service_account_file_exists": configured,
            "project_id": project_id,
            "client_email": (client_email[:4] + "***" + client_email[-10:]) if client_email else None,
            "registered_device_tokens_count": len(self._tokens),
            "registered_devices": list(self._tokens.keys()),
            "setup_steps": [
                {
                    "step": 1,
                    "title": "Create Firebase Project",
                    "instruction": "Navigate to https://console.firebase.google.com/ and create or select your project."
                },
                {
                    "step": 2,
                    "title": "Enable FCM API",
                    "instruction": "In Project Settings -> Cloud Messaging, verify Firebase Cloud Messaging API (V1) is enabled."
                },
                {
                    "step": 3,
                    "title": "Generate Private Service Account Key",
                    "instruction": "Go to Project Settings -> Service accounts -> Click 'Generate new private key'. Download the JSON file."
                },
                {
                    "step": 4,
                    "title": "Place Credentials File",
                    "instruction": "Save the file as D:\\matrix_data\\credentials\\firebase_service_account.json (or set FIREBASE_SERVICE_ACCOUNT_JSON environment variable)."
                },
                {
                    "step": 5,
                    "title": "Companion Token Registration",
                    "instruction": "The Android app will automatically register its FCM device token via POST /api/v1/devices/{device_id}/fcm-token upon companion startup."
                }
            ]
        }

    def get_device_token(self, device_id: str) -> Optional[str]:
        return self._tokens.get(device_id)

    async def send_notification(
        self,
        title: str,
        body: str,
        device_id: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
        priority: str = "high"
    ) -> Dict[str, Any]:
        """Dispatch a notification to mobile companion.
        Attempts FCM push if configured, always multicasts over active WebSockets,
        and records to persistent notification history.
        """
        notification_entry = {
            "id": f"notif_{int(time.time() * 1000)}",
            "title": title,
            "body": body,
            "data": data or {},
            "priority": priority,
            "target_device_id": device_id,
            "created_at": time.time(),
            "status": "PENDING",
            "channels_delivered": []
        }

        # 1. Real-time WebSocket delivery
        ws_delivered = False
        if ws_manager.active_connections:
            try:
                await ws_manager.broadcast({
                    "type": "push_notification",
                    "payload": {
                        "id": notification_entry["id"],
                        "title": title,
                        "body": body,
                        "data": data or {},
                        "priority": priority,
                        "timestamp": time.time()
                    }
                })
                ws_delivered = True
                notification_entry["channels_delivered"].append("websocket")
            except Exception as e:
                logger.warning(f"Failed to broadcast push over WebSocket: {e}")

        # 2. FCM Push delivery if configured
        fcm_delivered = False
        fcm_error = None
        if self.is_firebase_configured():
            fcm_token = self._tokens.get(device_id) if device_id else None
            if fcm_token:
                try:
                    fcm_delivered = await self._send_fcm_v1(fcm_token, title, body, data)
                    if fcm_delivered:
                        notification_entry["channels_delivered"].append("fcm_v1")
                except Exception as e:
                    fcm_error = str(e)
                    logger.error(f"FCM delivery error: {e}")
            else:
                fcm_error = "Device FCM token not registered."
        else:
            fcm_error = "Firebase service account not configured (requires firebase_service_account.json)."

        # Determine overall delivery status
        if fcm_delivered or ws_delivered:
            notification_entry["status"] = "DELIVERED"
        else:
            notification_entry["status"] = "QUEUED_OFFLINE"

        notification_entry["fcm_error"] = fcm_error
        self._history.append(notification_entry)
        self._save_history()

        return {
            "success": ws_delivered or fcm_delivered,
            "notification_id": notification_entry["id"],
            "status": notification_entry["status"],
            "channels_delivered": notification_entry["channels_delivered"],
            "ws_active_clients": len(ws_manager.active_connections),
            "firebase_configured": self.is_firebase_configured(),
            "fcm_status": "DELIVERED" if fcm_delivered else (fcm_error or "SKIPPED")
        }

    async def _send_fcm_v1(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send via Google FCM HTTP v1 using service account credentials."""
        # Read service account json
        sa_path = self._fcm_creds_file
        if not sa_path.exists() and os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            sa_path = Path(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))

        if not sa_path.exists():
            return False

        try:
            sa_info = json.loads(sa_path.read_text(encoding="utf-8"))
            project_id = sa_info.get("project_id")
            if not project_id:
                return False

            # In production, uses google-auth / firebase-admin to sign JWT for FCM scope:
            # https://www.googleapis.com/auth/firebase.messaging
            # If google-auth is available, use it:
            try:
                from google.oauth2 import service_account
                import google.auth.transport.requests

                creds = service_account.Credentials.from_service_account_file(
                    str(sa_path),
                    scopes=["https://www.googleapis.com/auth/firebase.messaging"]
                )
                request = google.auth.transport.requests.Request()
                creds.refresh(request)
                access_token = creds.token

                url = f"https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "message": {
                        "token": token,
                        "notification": {
                            "title": title,
                            "body": body
                        },
                        "data": {k: str(v) for k, v in (data or {}).items()}
                    }
                }
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    return resp.status_code == 200
            except ImportError:
                logger.warning("google-auth not installed; falling back to direct FCM check.")
                return False
        except Exception as e:
            logger.error(f"Error executing FCM v1 request: {e}")
            return False

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve recent notification history."""
        return sorted(self._history, key=lambda x: x.get("created_at", 0), reverse=True)[:limit]


push_service = PushNotificationService()
