"""MATRIX Configuration Management Module.
Centralizes environment settings, hardware profiles, path configurations, and security policies.

Storage resolution rules (in priority order):
  1. ``MATRIX_DATA_DIR`` environment variable (or ``.env`` entry).
  2. ``D:\\matrix_data`` when that drive exists *and* is writable.
  3. ``<repository>/data`` otherwise (portable fallback for CI, laptops, fresh installs).

All derived paths (database, models, cache, logs, local model file) follow the resolved
data root unless they are overridden explicitly. This keeps MATRIX runnable on machines
without a D: drive and on headless CI runners.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PORTABLE_DATA_DIR = PROJECT_ROOT / "data"
PREFERRED_DATA_DIR = Path("D:/matrix_data")


def _probe_writable(path: Path) -> bool:
    """Return True when ``path`` can be created and written to."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".matrix_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


@lru_cache(maxsize=1)
def resolve_data_dir() -> Path:
    """Resolve the storage root using the documented priority order."""
    configured = os.environ.get("MATRIX_DATA_DIR", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        # An explicitly configured root is honoured even if unusable so that the
        # resulting error is loud and attributable instead of silently relocated.
        return candidate if _probe_writable(candidate) else candidate

    if _probe_writable(PREFERRED_DATA_DIR):
        return PREFERRED_DATA_DIR
    return PORTABLE_DATA_DIR


def _physical_cores() -> int:
    """Detect physical CPU cores (falls back to logical count)."""
    try:
        import psutil

        return psutil.cpu_count(logical=False) or os.cpu_count() or 1
    except Exception:  # pragma: no cover - psutil is a hard dependency
        return os.cpu_count() or 1


def _logical_threads() -> int:
    """Detect logical CPU threads."""
    try:
        import psutil

        return psutil.cpu_count(logical=True) or os.cpu_count() or 1
    except Exception:  # pragma: no cover
        return os.cpu_count() or 1


def _low_ram_profile() -> bool:
    """True on machines with 12 GB RAM or less (the MATRIX target hardware class)."""
    try:
        import psutil

        return psutil.virtual_memory().total <= 12 * 1024**3
    except Exception:  # pragma: no cover
        return True


def _avx2_supported() -> bool:
    """Cheap AVX2 heuristic: every x86-64 CPU shipped since ~2013 supports it.

    This is advisory only; actual model selection is governed by
    ``ModelManager.benchmark_memory()`` at runtime.
    """
    import platform

    return platform.machine().lower() in {"amd64", "x86_64"}


class Settings(BaseSettings):
    """Global configuration settings for MATRIX."""

    # Core Application
    app_name: str = Field(default="MATRIX", alias="MATRIX_APP_NAME")
    env: str = Field(default="development", alias="MATRIX_ENV")
    version: str = Field(default="1.0.0", alias="MATRIX_VERSION")
    debug: bool = Field(default=False, alias="MATRIX_DEBUG")

    # Storage & Persistence (resolved dynamically, see module docstring)
    base_dir: Path = Field(default=PROJECT_ROOT, alias="MATRIX_BASE_DIR")
    data_dir: Path = Field(default_factory=resolve_data_dir, alias="MATRIX_DATA_DIR")
    database_url: str = Field(
        default_factory=lambda: "sqlite+aiosqlite:///"
        + (resolve_data_dir() / "matrix.db").as_posix(),
        alias="MATRIX_DATABASE_URL",
    )
    models_dir: Path = Field(
        default_factory=lambda: resolve_data_dir() / "models", alias="MATRIX_MODELS_DIR"
    )
    cache_dir: Path = Field(
        default_factory=lambda: resolve_data_dir() / "cache", alias="MATRIX_CACHE_DIR"
    )
    logs_dir: Path = Field(
        default_factory=lambda: resolve_data_dir() / "logs", alias="MATRIX_LOGS_DIR"
    )

    # Network & API
    host: str = Field(default="127.0.0.1", alias="MATRIX_HOST")
    port: int = Field(default=8000, alias="MATRIX_PORT")
    cors_origins: List[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:8000",
        ],
        alias="MATRIX_CORS_ORIGINS",
    )
    secret_key: str = Field(
        default="matrix_dev_super_secret_key_change_in_production_32char_min",
        alias="MATRIX_SECRET_KEY",
    )

    # Hardware Profile (auto-detected; override only for benchmarking or pinning)
    cpu_cores: int = Field(default_factory=_physical_cores, alias="MATRIX_CPU_CORES")
    cpu_threads: int = Field(default_factory=_logical_threads, alias="MATRIX_CPU_THREADS")
    avx2_enabled: bool = Field(default_factory=_avx2_supported, alias="MATRIX_AVX2_ENABLED")
    low_ram_mode: bool = Field(default_factory=_low_ram_profile, alias="MATRIX_LOW_RAM_MODE")
    max_ram_percent: float = Field(default=85.0, alias="MATRIX_MAX_RAM_PERCENT")

    # Local AI Model Settings (Qwen2.5 1.5B Q4_K_M candidate for 8 GB CPU-only hosts)
    local_model_name: str = Field(
        default="qwen2.5-1.5b-instruct", alias="MATRIX_LOCAL_MODEL_NAME"
    )
    local_model_path: Path = Field(
        default_factory=lambda: resolve_data_dir()
        / "models"
        / "qwen2.5-1.5b-instruct-q4_k_m.gguf",
        alias="MATRIX_LOCAL_MODEL_PATH",
    )
    embedding_model: str = Field(default="all-MiniLM-L6-v2", alias="MATRIX_EMBEDDING_MODEL")

    # Optional Cloud Providers
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    free_llm_api_endpoint: str = Field(default="", alias="FREE_LLM_API_ENDPOINT")

    # Voice & Interaction
    wake_word: str = Field(default="hey_matrix", alias="MATRIX_WAKE_WORD")
    speech_language: str = Field(default="en", alias="MATRIX_SPEECH_LANGUAGE")
    tts_voice: str = Field(default="en_US-lessac-medium", alias="MATRIX_TTS_VOICE")
    audio_input_device_index: Optional[int] = Field(
        default=None, alias="MATRIX_AUDIO_INPUT_DEVICE_INDEX"
    )
    audio_input_device_name: Optional[str] = Field(
        default=None, alias="MATRIX_AUDIO_INPUT_DEVICE_NAME"
    )
    audio_input_preferred_api: str = Field(default="WASAPI", alias="MATRIX_AUDIO_PREFERRED_API")
    audio_native_resampling: bool = Field(default=True, alias="MATRIX_AUDIO_NATIVE_RESAMPLING")
    voice_silence_duration_ms: int = Field(default=1200, alias="MATRIX_VOICE_SILENCE_MS")
    voice_playback_post_pause_ms: int = Field(
        default=850, alias="MATRIX_VOICE_PLAYBACK_POST_PAUSE_MS"
    )
    voice_speech_rate: str = Field(default="+0%", alias="MATRIX_VOICE_SPEECH_RATE")
    wake_word_sensitivity: float = Field(default=0.35, alias="MATRIX_WAKE_WORD_SENSITIVITY")

    # Telephony & Calling
    bland_api_key: str = Field(default="", alias="BLAND_API_KEY")
    bland_api_base_url: str = Field(default="https://api.bland.ai", alias="BLAND_API_BASE_URL")
    bland_target_phone: str = Field(default="", alias="BLAND_TARGET_PHONE")
    # Shared secret required on the Bland AI webhook (query param `secret` or the
    # X-Matrix-Webhook-Secret header). Unset means the webhook is refused as unconfigured.
    bland_webhook_secret: str = Field(default="", alias="MATRIX_BLAND_WEBHOOK_SECRET")

    # Security & Autonomy
    security_level: int = Field(default=3, alias="MATRIX_SECURITY_LEVEL")
    require_approval_high_risk: bool = Field(
        default=True, alias="MATRIX_REQUIRE_APPROVAL_HIGH_RISK"
    )
    # Shared bearer token for non-loopback clients (Android companion, LAN devices).
    # When empty, only loopback clients (or paired devices with valid tokens) are trusted.
    api_token: str = Field(default="", alias="MATRIX_API_TOKEN")
    # Arbitrary-code execution endpoints (/api/v1/developer/*) stay disabled unless
    # explicitly opted in. This prevents a local web page from reaching an RCE surface.
    developer_mode: bool = Field(default=False, alias="MATRIX_DEVELOPER_MODE")
    # Hosts allowed to reach privileged endpoints without a token.
    trusted_hosts: List[str] = Field(
        default=["127.0.0.1", "::1", "localhost", "testclient"],
        alias="MATRIX_TRUSTED_HOSTS",
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    def initialize_directories(self) -> List[Path]:
        """Ensure all required data, model, cache, and log directories exist.

        Returns the list of directories that could not be created (empty on success).
        """
        failed: List[Path] = []
        for path in (self.data_dir, self.models_dir, self.cache_dir, self.logs_dir):
            try:
                path.mkdir(parents=True, exist_ok=True)
            except OSError:
                failed.append(path)
        return failed

    @property
    def is_ci(self) -> bool:
        """True when running inside an automated CI environment."""
        return self.env.lower() in {"ci", "test"} or os.environ.get("CI") == "true"


# Global settings singleton
settings = Settings()
settings.initialize_directories()
