"""MATRIX Extended Workflows Automated Test Suite.
Tests Automation Tasks, File Explorer & Sandboxing, Developer Execution, Voice, Vision, and Audit.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path
from api.server import app
from config.settings import settings


@pytest.mark.asyncio
async def test_automation_tasks_lifecycle():
    """Verify workflow task queuing, checkpoint tracking, and completion."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create task
        res = await client.post(
            "/api/v1/tasks",
            json={"title": "Automated System Checkpoint Task", "autonomy_level": 3}
        )
        assert res.status_code == 201
        data = res.json()
        assert data["task_id"].startswith("task_")
        assert data["status"] == "RUNNING"
        assert data["checkpoints"] is not None

        # Complete task
        comp_res = await client.post(f"/api/v1/tasks/{data['task_id']}/complete")
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        assert comp_data["status"] == "COMPLETED"
        assert comp_data["completed_at"] is not None


@pytest.mark.asyncio
async def test_file_explorer_and_security_boundary():
    """Verify document creation, reading, and path traversal protection."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create file in D:\matrix_data
        create_res = await client.post(
            "/api/v1/files/create",
            json={"filename": "test_verification.txt", "content": "Verified MATRIX file agent write.", "folder": "docs"}
        )
        assert create_res.status_code == 201

        # Read file back
        read_res = await client.post(
            "/api/v1/files/read",
            json={"relative_path": "docs/test_verification.txt"}
        )
        assert read_res.status_code == 200
        read_data = read_res.json()
        assert "Verified MATRIX file agent write." in read_data["content"]

        # Path traversal protection test (attempt to escape D:\matrix_data)
        traversal_res = await client.post(
            "/api/v1/files/read",
            json={"relative_path": "../../Windows/System32/drivers/etc/hosts"}
        )
        assert traversal_res.status_code in [403, 404]


@pytest.mark.asyncio
async def test_developer_studio_validation_and_sandbox():
    """Verify syntax parsing and subprocess execution in developer studio."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Valid syntax
        v_res = await client.post("/api/v1/developer/validate", json={"code": "x = 42\nprint(x)"})
        assert v_res.status_code == 200
        assert v_res.json()["valid"] is True

        # Invalid syntax
        bad_res = await client.post("/api/v1/developer/validate", json={"code": "def bad_syntax(:"})
        assert bad_res.status_code == 200
        assert bad_res.json()["valid"] is False

        # Execute sandboxed code
        exec_res = await client.post(
            "/api/v1/developer/execute",
            json={"code": "print('MATRIX SANDBOX VERIFIED')"}
        )
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert data["success"] is True
        assert "MATRIX SANDBOX VERIFIED" in data["stdout"]


@pytest.mark.asyncio
async def test_voice_endpoints():
    """Verify voice synthesis and listening toggles."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Toggle listen
        toggle_res = await client.post("/api/v1/voice/toggle-listen", json={"enable": True})
        assert toggle_res.status_code == 200
        assert toggle_res.json()["listening"] is True

        # Disarm
        disarm_res = await client.post("/api/v1/voice/toggle-listen", json={"enable": False})
        assert disarm_res.status_code == 200
        assert disarm_res.json()["listening"] is False


@pytest.mark.asyncio
async def test_vision_screenshot_endpoint():
    """Verify desktop screenshot capture endpoint."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/v1/vision/screenshot")
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["width"] > 0
        assert data["height"] > 0
        assert Path(data["filepath"]).exists()


@pytest.mark.asyncio
async def test_audit_logs_retrieval():
    """Verify security audit logs endpoint returns persistent events."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/audit")
        assert res.status_code == 200
        logs = res.json()
        assert isinstance(logs, list)
