"""MATRIX Secure Account & Connector Registry.
Maintains persistent records of user-connected external accounts:
- Email (IMAP/SMTP/Exchange)
- Google Services (Gmail, Drive, Docs)
- GitHub (Repositories, Issues, Pull Requests)
- Cloud Storage (Dropbox, OneDrive, S3)
- Project Management & Developer Platforms

Security Enforcement:
1. Only explicitly user-connected accounts are accessible.
2. Credentials and tokens are stored in isolated vault (never logged or exposed in prompts).
3. Consequential changes (sending email, publishing, deleting) mandate Level 3 explicit authorization.
4. Token revocation and account disconnection supported.
5. If an account is not connected, MATRIX reports it truthfully and never hallucinates fake access.
"""
from typing import Dict, Any, List, Optional
import json
import base64
import hashlib
import time
from pathlib import Path
from datetime import datetime, timezone
from core.account_operations.models import (
    ConnectedAccount, ServiceType, AuthType, AccountStatus, AccountOperationRecord
)
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("core.account_registry")

ACCOUNT_DIR = Path(r"D:\matrix_data\accounts")
ACCOUNT_STORE = ACCOUNT_DIR / "accounts.json"
VAULT_STORE = ACCOUNT_DIR / "vault.dat"


class SecureAccountRegistry:
    """Manages authorized external service accounts and authentication tokens."""

    def __init__(self):
        ACCOUNT_DIR.mkdir(parents=True, exist_ok=True)
        self._accounts: Dict[str, ConnectedAccount] = {}
        self._vault: Dict[str, str] = {}
        self._load_from_disk()

    def _obfuscate(self, secret: str) -> str:
        """Obfuscate token for local storage."""
        b = secret.encode('utf-8')
        return base64.b64encode(b).decode('utf-8')

    def _deobfuscate(self, obfuscated: str) -> str:
        """Deobfuscate token."""
        try:
            return base64.b64decode(obfuscated.encode('utf-8')).decode('utf-8')
        except Exception:
            return ""

    def _load_from_disk(self):
        """Load registered accounts from persistent storage."""
        if ACCOUNT_STORE.exists():
            try:
                with open(ACCOUNT_STORE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for acc_id, data in raw.items():
                        self._accounts[acc_id] = ConnectedAccount(**data)
                logger.info(f"Loaded {len(self._accounts)} connected account(s) from registry.")
            except Exception as e:
                logger.error(f"Error loading accounts: {e}")

        if VAULT_STORE.exists():
            try:
                with open(VAULT_STORE, "r", encoding="utf-8") as f:
                    self._vault = json.load(f)
            except Exception as e:
                logger.error(f"Error loading vault: {e}")

    def _save_to_disk(self):
        """Persist registered accounts and vault."""
        try:
            with open(ACCOUNT_STORE, "w", encoding="utf-8") as f:
                serializable = {k: v.model_dump(mode="json") for k, v in self._accounts.items()}
                json.dump(serializable, f, indent=2)

            with open(VAULT_STORE, "w", encoding="utf-8") as f:
                json.dump(self._vault, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving account registry: {e}")

    def list_connected_accounts(self) -> List[Dict[str, Any]]:
        """List all currently authorized accounts (sanitized, zero credentials)."""
        return [
            {
                "account_id": a.account_id,
                "service_name": a.service_name,
                "service_type": a.service_type.value,
                "account_identifier": a.account_identifier,
                "auth_type": a.auth_type.value,
                "status": a.status.value,
                "permissions_granted": a.permissions_granted,
                "created_at": a.created_at.isoformat(),
                "last_synced_at": a.last_synced_at.isoformat() if a.last_synced_at else None
            }
            for a in self._accounts.values()
            if a.status == AccountStatus.CONNECTED
        ]

    def register_account(
        self,
        service_name: str,
        service_type: ServiceType,
        account_identifier: str,
        auth_type: AuthType,
        raw_credential: str,
        permissions: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ConnectedAccount:
        """Register and securely store a new user-authorized account."""
        acc_id = f"acc_{service_name.lower()}_{hashlib.sha256(account_identifier.encode()).hexdigest()[:8]}"
        cred_ref = f"ref_{acc_id}_{int(time.time())}"

        self._vault[cred_ref] = self._obfuscate(raw_credential)

        account = ConnectedAccount(
            account_id=acc_id,
            service_name=service_name,
            service_type=service_type,
            account_identifier=account_identifier,
            auth_type=auth_type,
            status=AccountStatus.CONNECTED,
            permissions_granted=permissions,
            credential_ref=cred_ref,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {}
        )

        self._accounts[acc_id] = account
        self._save_to_disk()
        logger.info(f"Account registered: [{service_name}] for identifier: '{account_identifier}'")
        return account

    def disconnect_account(self, account_id: str) -> bool:
        """Revoke and remove a connected account."""
        if account_id in self._accounts:
            acc = self._accounts[account_id]
            if acc.credential_ref in self._vault:
                del self._vault[acc.credential_ref]
            acc.status = AccountStatus.DISCONNECTED
            self._save_to_disk()
            logger.info(f"Account disconnected: [{acc.service_name}] ({account_id})")
            return True
        return False

    def get_account_by_service(self, service_name: str) -> Optional[ConnectedAccount]:
        """Find the active authorized account for a given service."""
        s_clean = service_name.lower().strip()
        for a in self._accounts.values():
            if a.service_name.lower() == s_clean and a.status == AccountStatus.CONNECTED:
                return a
        return None

    def get_credential(self, credential_ref: str) -> Optional[str]:
        """Retrieve credential internally for authorized operations only."""
        if credential_ref in self._vault:
            return self._deobfuscate(self._vault[credential_ref])
        return None


# Global Account Registry singleton
account_registry = SecureAccountRegistry()
