"""Lifecycle and data-integrity regression tests (audit milestone 3).

Guards three behaviours that previously produced silent side effects:
  * importing MATRIX must not arm microphone/wake-word monitoring
  * re-registering an unchanged capability must not rewrite a tracked file
  * provider webhooks must not accept unauthenticated callbacks
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import app
from config.settings import settings


def _local_client(host: str = "127.0.0.1") -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app, client=(host, 5000)),
        base_url="http://test",
    )


def test_importing_voice_manager_does_not_arm_microphone():
    """A bare import must not start wake-word inference or open an audio stream."""
    project_root = Path(__file__).resolve().parent.parent
    code = (
        "from voice.conversation.manager import hands_free_manager\n"
        "from voice.wake_word.engine import wake_word_detector\n"
        "print(int(hands_free_manager.wake_word_armed))\n"
        "print(int(wake_word_detector.is_listening))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=120,
        env=os.environ.copy(),
    )
    assert result.returncode == 0, result.stderr[-2000:]
    armed, listening = result.stdout.strip().splitlines()[-2:]
    assert armed == "0", "importing the voice manager armed the wake-word engine"
    assert listening == "0", "importing the voice manager opened the microphone"


def test_capability_registry_register_is_idempotent():
    """Re-registering identical data must not bump timestamps or rewrite the file."""
    from core.capability_registry.registry import CapabilityRegistry, ToolCapability

    store = settings.data_dir / "test_workspace" / "registry_test" / "capabilities.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    store.unlink(missing_ok=True)
    registry = CapabilityRegistry(store)
    capability = ToolCapability(
        capability_id="cap_test_idempotent",
        name="Idempotent Capability",
        description="Used to verify registry write behaviour.",
        category="Testing",
    )

    assert registry.register(capability) is True
    first = json.loads(store.read_text(encoding="utf-8"))
    first_stamp = first["cap_test_idempotent"]["last_updated"]
    first_mtime = store.stat().st_mtime_ns

    # Same capability, freshly constructed -> must be a no-op.
    identical = ToolCapability(**capability.model_dump())
    assert registry.register(identical) is True

    second = json.loads(store.read_text(encoding="utf-8"))
    assert second["cap_test_idempotent"]["last_updated"] == first_stamp
    assert store.stat().st_mtime_ns == first_mtime, "registry rewrote an unchanged file"


@pytest.mark.asyncio
async def test_bland_webhook_refuses_when_secret_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "bland_webhook_secret", "")
    async with _local_client() as client:
        res = await client.post("/api/v1/telephony/bland/webhook", json={"call_id": "c1"})
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_bland_webhook_rejects_wrong_secret(monkeypatch):
    monkeypatch.setattr(settings, "bland_webhook_secret", "expected-secret")
    async with _local_client() as client:
        res = await client.post(
            "/api/v1/telephony/bland/webhook",
            json={"call_id": "c1"},
            headers={"X-Matrix-Webhook-Secret": "wrong-secret"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_bland_webhook_accepts_matching_secret(monkeypatch):
    monkeypatch.setattr(settings, "bland_webhook_secret", "expected-secret")
    async with _local_client() as client:
        res = await client.post(
            "/api/v1/telephony/bland/webhook",
            json={"call_id": "call_abc", "status": "completed"},
            headers={"X-Matrix-Webhook-Secret": "expected-secret"},
        )
        assert res.status_code == 200
        assert res.json()["status"] == "RECEIVED"


@pytest.mark.asyncio
async def test_developer_execution_is_rate_limited(monkeypatch):
    """The 11th execution inside the window must be throttled."""
    monkeypatch.setattr(settings, "developer_mode", True)
    async with _local_client("127.0.0.10") as client:
        statuses = []
        for _ in range(11):
            res = await client.post(
                "/api/v1/developer/execute", json={"code": "print('ok')"}
            )
            statuses.append(res.status_code)
        assert statuses[:10] == [200] * 10
        assert statuses[10] == 429
