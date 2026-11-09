"""MATRIX Configuration Management Module.
Centralizes environment settings, hardware profiles, path configurations, and security policies.
"""
from pathlib import Path
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global configuration settings for MATRIX."""

    # Core Application
    app_name: str = Field(default="MATRIX", alias="MATRIX_APP_NAME")
    env: str = Field(default="development", alias="MATRIX_ENV")
    version: str = Field(default="1.0.0", alias="MATRIX_VERSION")
    debug: bool = Field(default=True, alias="MATRIX_DEBUG")

    # Storage & Persistence (Stored on D:\matrix_data to conserve C: drive space)
    base_dir: Path = Field(default=Path(__file__).resolve().parent.parent, alias="MATRIX_BASE_DIR")
    data_dir: Path = Field(default=Path("D:/matrix_data"), alias="MATRIX_DATA_DIR")
    database_url: str = Field(
        default="sqlite+aiosqlite:///D:/matrix_data/matrix.db",
        alias="MATRIX_DATABASE_URL"
    )
    models_dir: Path = Field(default=Path("D:/matrix_data/models"), alias="MATRIX_MODELS_DIR")
    cache_dir: Path = Field(default=Path("D:/matrix_data/cache"), alias="MATRIX_CACHE_DIR")
    logs_dir: Path = Field(default=Path("logs"), alias="MATRIX_LOGS_DIR")

    # Network & API
    host: str = Field(default="127.0.0.1", alias="MATRIX_HOST")
    port: int = Field(default=8000, alias="MATRIX_PORT")
    cors_origins: List[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        alias="MATRIX_CORS_ORIGINS"
    )
    secret_key: str = Field(
        default="matrix_dev_super_secret_key_change_in_production_32char_min",
        alias="MATRIX_SECRET_KEY"
    )

    # Hardware Profile (AMD Ryzen 7 5700U 8C/16T, 8 GB RAM, Radeon Graphics)
    cpu_cores: int = Field(default=8, alias="MATRIX_CPU_CORES")
    cpu_threads: int = Field(default=16, alias="MATRIX_CPU_THREADS")
    avx2_enabled: bool = Field(default=True, alias="MATRIX_AVX2_ENABLED")
    low_ram_mode: bool = Field(default=True, alias="MATRIX_LOW_RAM_MODE")
    max_ram_percent: float = Field(default=85.0, alias="MATRIX_MAX_RAM_PERCENT")

    # Local AI Model Settings (Qwen2.5 1.5B Q4_K_M Candidate)
    local_model_name: str = Field(default="qwen2.5-1.5b-instruct", alias="MATRIX_LOCAL_MODEL_NAME")
    local_model_path: Path = Field(
        default=Path("D:/matrix_data/models/qwen2.5-1.5b-instruct-q4_k_m.gguf"),
        alias="MATRIX_LOCAL_MODEL_PATH"
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
    audio_input_device_index: Optional[int] = Field(default=None, alias="MATRIX_AUDIO_INPUT_DEVICE_INDEX")
    audio_input_device_name: Optional[str] = Field(default=None, alias="MATRIX_AUDIO_INPUT_DEVICE_NAME")
    audio_input_preferred_api: str = Field(default="WASAPI", alias="MATRIX_AUDIO_PREFERRED_API")
    audio_native_resampling: bool = Field(default=True, alias="MATRIX_AUDIO_NATIVE_RESAMPLING")
    voice_silence_duration_ms: int = Field(default=1200, alias="MATRIX_VOICE_SILENCE_MS")
    voice_playback_post_pause_ms: int = Field(default=850, alias="MATRIX_VOICE_PLAYBACK_POST_PAUSE_MS")
    voice_speech_rate: str = Field(default="+0%", alias="MATRIX_VOICE_SPEECH_RATE")
    wake_word_sensitivity: float = Field(default=0.35, alias="MATRIX_WAKE_WORD_SENSITIVITY")

    # Telephony & Calling
    bland_api_key: str = Field(default="", alias="BLAND_API_KEY")
    bland_api_base_url: str = Field(default="https://api.bland.ai", alias="BLAND_API_BASE_URL")
    bland_target_phone: str = Field(default="+919193002500", alias="BLAND_TARGET_PHONE")

    # Security & Autonomy
    security_level: int = Field(default=3, alias="MATRIX_SECURITY_LEVEL")
    require_approval_high_risk: bool = Field(
        default=True, alias="MATRIX_REQUIRE_APPROVAL_HIGH_RISK"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def initialize_directories(self) -> None:
        """Ensure all required data, model, cache, and log directories exist."""
        for path in [self.data_dir, self.models_dir, self.cache_dir, self.logs_dir]:
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                # If secondary drive is temporarily unreachable, fallback to local directory
                fallback = Path.cwd() / "data" / path.name
                fallback.mkdir(parents=True, exist_ok=True)


# Global settings singleton
settings = Settings()
settings.initialize_directories()
