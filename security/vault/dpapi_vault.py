"""MATRIX DPAPI Encrypted Credential Vault.
Provides user-bound Windows DPAPI encryption for sensitive API keys, OAuth tokens, and secrets.
Guarantees zero plaintext secrets in Git, logs, or unencrypted storage on disk.
"""
from typing import Dict, Any, List, Optional
import os
import json
from pathlib import Path
from config.settings import settings
from config.logging_config import get_logger

logger = get_logger("security.vault")

VAULT_DIR = Path(r"D:\matrix_data\security")
VAULT_FILE = VAULT_DIR / "dpapi_vault.dat"


class DPAPIVault:
    """Manages encrypted secrets using native Windows Data Protection API (DPAPI)."""

    def __init__(self, vault_path: Optional[Path] = None):
        self.vault_path = vault_path or VAULT_FILE
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, str] = {}
        self._load_vault()

    def _encrypt(self, plaintext: str) -> bytes:
        """Encrypt string using Windows DPAPI."""
        try:
            import win32crypt
            data = plaintext.encode("utf-8")
            return win32crypt.CryptProtectData(data, "MATRIX_CREDENTIAL_VAULT", None, None, None, 0)
        except Exception as e:
            logger.error(f"DPAPI encryption failed: {e}")
            raise RuntimeError(f"DPAPI encryption unavailable: {e}")

    def _decrypt(self, ciphertext: bytes) -> str:
        """Decrypt bytes using Windows DPAPI."""
        try:
            import win32crypt
            _, decrypted = win32crypt.CryptUnprotectData(ciphertext, None, None, None, 0)
            return decrypted.decode("utf-8")
        except Exception as e:
            logger.error(f"DPAPI decryption failed: {e}")
            raise RuntimeError(f"DPAPI decryption failed: {e}")

    def _load_vault(self):
        """Load and decrypt vault contents into memory cache."""
        if not self.vault_path.exists():
            self._cache = {}
            return

        try:
            encrypted_data = self.vault_path.read_bytes()
            if not encrypted_data:
                self._cache = {}
                return
            decrypted_json = self._decrypt(encrypted_data)
            self._cache = json.loads(decrypted_json)
            logger.info(f"Loaded {len(self._cache)} encrypted secrets from DPAPI vault.")
        except Exception as e:
            logger.warning(f"Could not read DPAPI vault (initializing fresh): {e}")
            self._cache = {}

    def _save_vault(self):
        """Encrypt and write current memory cache to disk."""
        try:
            json_str = json.dumps(self._cache)
            encrypted_bytes = self._encrypt(json_str)
            self.vault_path.write_bytes(encrypted_bytes)
            logger.debug(f"Saved {len(self._cache)} secrets to DPAPI vault.")
        except Exception as e:
            logger.error(f"Failed to persist DPAPI vault to disk: {e}")
            raise

    def store_secret(self, key: str, value: str) -> bool:
        """Store or update a secret key in the encrypted vault."""
        if not key or not isinstance(key, str):
            return False
        clean_key = key.strip().upper()
        self._cache[clean_key] = str(value)
        self._save_vault()
        logger.info(f"Secret '{clean_key}' securely stored in DPAPI vault.")
        return True

    def retrieve_secret(self, key: str) -> Optional[str]:
        """Retrieve a decrypted secret from the vault."""
        clean_key = (key or "").strip().upper()
        return self._cache.get(clean_key)

    def delete_secret(self, key: str) -> bool:
        """Remove a secret from the vault."""
        clean_key = (key or "").strip().upper()
        if clean_key in self._cache:
            del self._cache[clean_key]
            self._save_vault()
            logger.info(f"Secret '{clean_key}' removed from DPAPI vault.")
            return True
        return False

    def list_keys(self) -> List[str]:
        """List secret key identifiers without revealing values."""
        return sorted(list(self._cache.keys()))

    def get_masked_catalog(self) -> Dict[str, str]:
        """Return catalog of stored keys with masked values for UI inspection."""
        catalog = {}
        for k, v in self._cache.items():
            if len(v) <= 8:
                catalog[k] = "***"
            else:
                catalog[k] = f"{v[:4]}...{v[-4:]}"
        return catalog


# Global singleton vault
dpapi_vault = DPAPIVault()
