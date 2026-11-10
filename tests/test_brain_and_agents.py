"""MATRIX Comprehensive Automated Test Suite: Brain, Agents, Memory, and Repo Intelligence.
Tests end-to-end execution, intent parsing, planning, all specialized agents, and device sync.
"""
import pytest
from httpx import AsyncClient, ASGITransport
from pathlib import Path

from core.model_manager import model_manager
from core.intent_engine import intent_engine, IntentType
from core.reasoning_engine import reasoning_engine
from core.task_router import task_router
from core.orchestrator import orchestrator
from core.brain import brain
from core.pairing_manager import pairing_manager
from repository_engine.github_scanner import github_scanner
from repository_engine.repository_analyzer import repository_analyzer
from api.server import app

# Register test pairing token for this test suite only.
# This token is NOT present in production - it is isolated to the test fixture.
_pairing_token = pairing_manager.create_token(ttl_seconds=300)
# Replace the registry with just the test token so lifecycle tests work cleanly
from core.pairing_manager import PairingTokenRecord
pairing_manager._registry.clear()
pairing_manager._registry["mtx_pair_valid_test_token"] = PairingTokenRecord(token="mtx_pair_valid_test_token", ttl_seconds=300)


@pytest.mark.asyncio
async def test_model_manager_and_memory_benchmark():
    """Verify memory benchmarking calculates safe parameter thresholds."""
    bench = model_manager.benchmark_memory()
    assert bench.total_ram_mb > 0
    assert bench.available_ram_mb > 0
    assert bench.recommended_model.startswith("qwen2.5")
    assert bench.max_safe_params_billion <= 3.5

    # Test generation
    res = await model_manager.generate_response("what is matrix?")
    assert res.content is not None
    assert len(res.content) > 10
    assert res.is_local is True


@pytest.mark.asyncio
async def test_intent_engine_classification():
    """Verify intent extraction across commands, research, coding, and telemetry."""
    i_cmd = intent_engine.classify("Open notepad")
    assert i_cmd.intent_type == IntentType.COMMAND
    assert i_cmd.target_agent == "computer"

    i_res = intent_engine.classify("Search the web for quantum computing")
    assert i_res.intent_type == IntentType.RESEARCH
    assert i_res.target_agent == "research"

    i_code = intent_engine.classify("Write a python script to test API endpoints")
    assert i_code.intent_type == IntentType.CODING
    assert i_code.target_agent == "coding"

    i_sys = intent_engine.classify("Check how much RAM is being used")
    assert i_sys.intent_type == IntentType.SYSTEM
    assert i_sys.target_agent == "system"


@pytest.mark.asyncio
async def test_reasoning_and_planner():
    """Verify reasoning engine generates multi-step plans with verification contracts."""
    intent = intent_engine.classify("Search the web for autonomous agents")
    plan = reasoning_engine.create_plan(intent)
    assert len(plan.steps) >= 2
    assert plan.steps[0].verification_hook == "verify_sources_found"
    assert plan.steps[1].verification_hook == "verify_markdown_generated"
    assert plan.status == "PENDING"


@pytest.mark.asyncio
async def test_specialized_agents_dispatch():
    """Verify that task router dispatches to specialized agents and gets verified results."""
    # 1. System Agent
    sys_res = await task_router.dispatch("system", "poll_telemetry", {})
    assert sys_res.success is True
    assert "cpu" in sys_res.data
    assert "memory" in sys_res.data

    # 2. Repo Intel Agent
    repo_res = await task_router.dispatch("repo_intel", "query_inventory", {"query": "hexstrike"})
    assert repo_res.success is True
    assert repo_res.data["total_cataloged"] == 65
    assert repo_res.data["matched_count"] >= 1

    # 3. Security Agent
    sec_res = await task_router.dispatch("security", "evaluate_payload", {"command": "dir"})
    assert sec_res.success is True
    assert sec_res.data["safe"] is True

    sec_bad = await task_router.dispatch("security", "evaluate_payload", {"command": "format C: /fs:NTFS"})
    assert sec_bad.success is False

    # 4. Coding Agent
    code_res = await task_router.dispatch("coding", "validate_syntax", {"code": "def hello():\n    return 'matrix'\n"})
    assert code_res.success is True


@pytest.mark.asyncio
async def test_orchestrator_execution_pipeline():
    """Verify orchestrator runs OBSERVE -> PLAN -> EXECUTE -> VERIFY -> REPORT."""
    res = await orchestrator.execute_request("Check CPU specs and RAM usage")
    assert res.plan.status == "COMPLETED"
    assert len(res.results) > 0
    assert "Telemetry nominal" in res.response_text or "CPU" in res.response_text


@pytest.mark.asyncio
async def test_brain_facade():
    """Verify MATRIX Brain processes user requests and persists conversation turns."""
    result = await brain.process_user_request(
        session_id="sess_test_brain",
        user_prompt="Who are you and what can you do?"
    )
    assert result["session_id"] == "sess_test_brain"
    assert len(result["response"]) > 10
    assert result["plan_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_repository_intelligence_pipeline():
    """Verify all 65 starred repositories are cataloged, analyzed, and hardware-checked."""
    repos = github_scanner.load_inventory()
    assert len(repos) == 65

    assessments = repository_analyzer.analyze_all()
    assert len(assessments) == 65
    categories = {a.category for a in assessments}
    assert "Security & MCP" in categories
    assert "Voice & Audio" in categories
    assert "Browser & Web" in categories


@pytest.mark.asyncio
async def test_device_pairing_api():
    """Verify device pairing endpoint authorizes mobile companion."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        pair_resp = await client.post(
            "/api/v1/devices/pair",
            json={
                "device_id": "test_pixel_phone_01",
                "name": "User Pixel 8 Pro",
                "platform": "android",
                "pairing_token": "mtx_pair_valid_test_token"
            }
        )
        assert pair_resp.status_code == 200
        pair_data = pair_resp.json()
        assert pair_data["status"] == "PAIRED"
        assert pair_data["auth_token"].startswith("mtx_auth_")

        # List devices
        list_resp = await client.get("/api/v1/devices")
        assert list_resp.status_code == 200
        devices = list_resp.json()
        device_ids = [d["device_id"] for d in devices]
        assert "test_pixel_phone_01" in device_ids


@pytest.mark.asyncio
async def test_memory_crud_api():
    """Verify memory CRUD endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create memory
        create_resp = await client.post(
            "/api/v1/memory",
            json={"key": "user_spoken_name", "value": {"name": "Ayaan", "title": "Architect"}, "category": "profile"}
        )
        assert create_resp.status_code == 201

        # List memories
        list_resp = await client.get("/api/v1/memory")
        assert list_resp.status_code == 200
        items = list_resp.json()
        keys = [item["key"] for item in items]
        assert "user_spoken_name" in keys

        # Delete memory
        del_resp = await client.delete("/api/v1/memory/user_spoken_name")
        assert del_resp.status_code == 200
        assert del_resp.json()["status"] == "DELETED"
