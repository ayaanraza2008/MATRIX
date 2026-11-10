"""MATRIX Phase 1 Foundation Automated Test Suite.
Validates configuration, database integrity, REST API endpoints, and system telemetry.
"""
import pytest
import psutil
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from sqlalchemy import select

from config.settings import settings
from database.session import engine, AsyncSessionLocal
from database.models import UserPreference, Session as SessionModel, Message as MessageModel
from database.init_db import init_database
from api.server import app


@pytest.mark.asyncio
async def test_settings_and_paths():
    """Verify configuration resolves a usable, portable storage layout."""
    assert settings.app_name == "MATRIX"
    assert settings.cpu_cores >= 1
    assert settings.cpu_threads >= settings.cpu_cores
    assert settings.data_dir.exists() and settings.data_dir.is_dir()
    # Storage contract: database always follows the resolved data root.
    assert settings.database_url.startswith("sqlite+aiosqlite:///")
    assert (settings.data_dir / "matrix.db").as_posix() in settings.database_url


@pytest.mark.asyncio
async def test_database_initialization():
    """Verify database initializes tables and seeds identity preference."""
    db_initialized = await init_database()
    assert db_initialized is True

    async with AsyncSessionLocal() as session:
        stmt = select(UserPreference).where(UserPreference.key == "system_identity")
        result = await session.execute(stmt)
        pref = result.scalar_one_or_none()
        assert pref is not None
        assert pref.value["assistant_name"] == "MATRIX"
        assert "English" in pref.value["languages"]


@pytest.mark.asyncio
async def test_health_endpoint():
    """Verify /api/v1/health returns HTTP 200, valid telemetry, and healthy status."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert data["status"] in ["healthy", "nominal", "degraded"]
        assert data["app_name"] == "MATRIX"
        assert data["database"]["connected"] is True
        assert data["database"]["type"] == "SQLite (Async aiosqlite)"

        # Verify real hardware telemetry matches what the host reports
        assert "system" in data
        assert data["system"]["cpu_cores_physical"] == psutil.cpu_count(logical=False)
        assert data["system"]["cpu_threads_logical"] == psutil.cpu_count(logical=True)
        assert data["system"]["ram_total_mb"] > 0
        assert data["system"]["ram_used_mb"] > 0
        assert "storage" in data
        assert len(data["storage"]) >= 1
        assert any(info.get("total_gb", 0) > 0 for info in data["storage"].values())


@pytest.mark.asyncio
async def test_system_info_and_metrics():
    """Verify system spec info and live metrics endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        info_resp = await client.get("/api/v1/system/info")
        assert info_resp.status_code == 200
        info_data = info_resp.json()
        assert info_data["hardware"]["physical_cores"] == psutil.cpu_count(logical=False)
        assert info_data["hardware"]["logical_processors"] == psutil.cpu_count(logical=True)
        cpu_name = info_data["hardware"]["cpu_name"]
        assert isinstance(cpu_name, str) and cpu_name.strip()
        assert cpu_name != "unreported", "CPU model should be detectable on this host"

        metrics_resp = await client.get("/api/v1/system/metrics")
        assert metrics_resp.status_code == 200
        metrics_data = metrics_resp.json()
        assert "cpu" in metrics_data
        assert "memory" in metrics_data
        assert metrics_data["memory"]["percent"] > 0


@pytest.mark.asyncio
async def test_sessions_and_messages_crud():
    """Verify session creation, message insertion, and retrieval in SQLite."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create session
        create_resp = await client.post("/api/v1/sessions", json={"title": "Test Mission alpha", "active_agent": "core"})
        assert create_resp.status_code == 201
        sess_data = create_resp.json()
        session_id = sess_data["session_id"]
        assert session_id.startswith("sess_")

        # Post message
        msg_resp = await client.post(
            f"/api/v1/sessions/{session_id}/messages",
            json={"role": "user", "content": "Jarvis, initialize diagnostic scan.", "agent_name": "core"}
        )
        assert msg_resp.status_code == 201
        msg_data = msg_resp.json()
        assert msg_data["content"] == "Jarvis, initialize diagnostic scan."

        # Retrieve messages
        list_msg_resp = await client.get(f"/api/v1/sessions/{session_id}/messages")
        assert list_msg_resp.status_code == 200
        messages = list_msg_resp.json()
        assert len(messages) == 1
        assert messages[0]["session_id"] == session_id


@pytest.mark.asyncio
async def test_capabilities_registry():
    """Verify capabilities route returns registered skills."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/capabilities")
        assert resp.status_code == 200
        caps = resp.json()
        assert len(caps) >= 6
        cap_ids = [c["capability_id"] for c in caps]
        assert "core_orchestrator" in cap_ids
        assert "computer_control" in cap_ids
        assert "voice_interaction" in cap_ids
        assert "browser_intelligence" in cap_ids


@pytest.mark.asyncio
async def test_ui_root_served():
    """Verify that root endpoint serves the React application index.html."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        # Should either be the HTML or json if not built
        assert "<!doctype html>" in resp.text.lower() or "MATRIX" in resp.text
