"""Security regression tests for MATRIX API hardening.

Covers the vulnerabilities fixed in the audit milestone:
  * path traversal / absolute-path writes through ``/api/v1/files``
  * unauthenticated remote access to privileged endpoints
  * Developer Studio code execution being disabled by default
  * WebSocket broker rejecting anonymous remote clients
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from api.server import app
from config.settings import settings
from security.path_guard import PathTraversalError, is_safe_name, resolve_within


def _remote_client() -> AsyncClient:
    """An HTTP client whose source address is a public IP, i.e. not loopback."""
    return AsyncClient(
        transport=ASGITransport(app=app, client=("203.0.113.7", 54321)),
        base_url="http://test",
    )


@pytest.mark.asyncio
async def test_remote_client_cannot_reach_privileged_routes_without_credentials():
    async with _remote_client() as client:
        res = await client.get("/api/v1/files")
        assert res.status_code == 401
        assert "Non-local clients" in res.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path",
    ["/api/v1/memory", "/api/v1/sessions", "/api/v1/capabilities", "/api/v1/voice/status"],
)
async def test_remote_client_blocked_on_formerly_open_routers(path):
    """The network gate covers every /api/ route, not just the hardened ones."""
    async with _remote_client() as client:
        res = await client.get(path)
        assert res.status_code == 401, f"{path} was reachable without credentials"


@pytest.mark.asyncio
async def test_health_endpoint_stays_public_for_remote_clients():
    async with _remote_client() as client:
        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.json()["app_name"] == "MATRIX"


@pytest.mark.asyncio
async def test_remote_client_with_api_token_is_allowed(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "test-shared-token")
    async with _remote_client() as client:
        res = await client.get(
            "/api/v1/files", headers={"Authorization": "Bearer test-shared-token"}
        )
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_remote_client_with_wrong_api_token_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "api_token", "test-shared-token")
    async with _remote_client() as client:
        res = await client.get(
            "/api/v1/files", headers={"Authorization": "Bearer wrong-token"}
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_local_client_is_trusted_by_default():
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/files")
        assert res.status_code == 200


@pytest.mark.asyncio
async def test_developer_execute_disabled_by_default(monkeypatch):
    """Even from localhost, code execution requires MATRIX_DEVELOPER_MODE=true."""
    monkeypatch.setattr(settings, "developer_mode", False)
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/developer/execute", json={"code": "print('should not run')"}
        )
        assert res.status_code == 403


@pytest.mark.asyncio
async def test_developer_execute_works_when_explicitly_enabled(monkeypatch):
    monkeypatch.setattr(settings, "developer_mode", True)
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/developer/execute", json={"code": "print('sandbox-ok')"}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert "sandbox-ok" in body["stdout"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename,folder",
    [
        ("../escaped.txt", "documents"),
        ("..\\escaped.txt", "documents"),
        ("note.txt", "../../outside"),
        ("C:\\Windows\\Temp\\pwned.txt", "documents"),
        ("/etc/passwd", "documents"),
    ],
)
async def test_file_create_rejects_traversal(filename, folder):
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/files/create",
            json={"filename": filename, "content": "x", "folder": folder},
        )
        assert res.status_code in (400, 403), res.text
        assert not (settings.data_dir.parent / "escaped.txt").exists()


@pytest.mark.asyncio
async def test_file_read_rejects_traversal():
    transport = ASGITransport(app=app, client=("127.0.0.1", 5000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/files/read",
            json={"relative_path": "../../Windows/System32/drivers/etc/hosts"},
        )
        assert res.status_code in (403, 404)


def test_path_guard_unit_contract():
    root = settings.data_dir
    assert resolve_within(root, "docs", "note.txt").name == "note.txt"
    for bad in ("../x", "a/../../b", "/abs/path", "C:\\Windows\\win.ini"):
        with pytest.raises(PathTraversalError):
            resolve_within(root, bad)


def test_safe_name_validation():
    assert is_safe_name("research_dossier.md")
    assert is_safe_name("v2.1.0-beta")
    assert not is_safe_name("..")
    assert not is_safe_name("a/b")
    assert not is_safe_name("")


@pytest.mark.asyncio
async def test_websocket_rejects_anonymous_remote_client():
    """The event broker must close sockets from non-local clients without a token."""
    from starlette.testclient import TestClient

    client = TestClient(
        app,
        base_url="http://test",
        client=("203.0.113.9", 5000),
    )
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/events") as ws:
            ws.receive_text()
