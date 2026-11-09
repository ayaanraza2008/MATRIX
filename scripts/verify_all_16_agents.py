"""MATRIX All 16 Specialized Agents Full Lifecycle Verification Script.
For EACH of the 16 agents:
1. Discovery & registration via AgentRegistry.
2. Capability inspection.
3. Security authorization evaluation.
4. Real functional action execution via TaskRouter.dispatch.
5. Verification of returned AgentResult.
6. Error propagation test (invalid parameters trigger structured FAILED status, never uncaught exceptions).
"""
import sys
import time
import json
import asyncio
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.task_router import task_router
from security.permissions.authorization_center import authorization_center

AGENTS_SUITE = [
    ("system", "diagnose_system", {}, "invalid_action_xyz", {}, "Hardware & CPU Diagnostics"),
    ("files", "list_directory", {"path": "D:\\matrix_data"}, "read_file", {"filepath": "C:\\nonexistent_98765.txt"}, "Filesystem & Document Operations"),
    ("computer", "query_status", {}, "launch", {"app": "totally_invalid_app_xyz"}, "Desktop Automation & UI Control"),
    ("browser", "search", {"query": "Python asyncio tutorial"}, "navigate", {"url": "http://invalid-non-existent-domain-xyz-98765.xyz"}, "Headless Browser & Web Extraction"),
    ("research", "web_research", {"topic": "AMD Ryzen 5700U architecture"}, "invalid_op", {}, "Multi-Source Research Synthesizer"),
    ("data_analysis", "calculate", {"expression": "25 * 4"}, "calculate", {"expression": "10 / 0"}, "Mathematical Calculation & Statistics"),
    ("coding", "inspect_code", {"code": "def hello():\n    return 'world'\n"}, "syntax", {"code": "def bad_syntax(:"}, "AST Analysis & Code Review"),
    ("creative", "generate_mermaid", {"title": "Test Architecture", "nodes": ["Frontend", "Backend", "Database"]}, "invalid_creative", {}, "Diagrams & Visual Blueprinting"),
    ("personal", "report_time_date", {}, "invalid_personal", {}, "Personal Assistant & Scheduling"),
    ("android", "generate_pairing_token", {"port": 8000, "ttl": 300}, "invalid_android", {}, "Android Companion & Push Bridge"),
    ("memory", "list_memory", {}, "invalid_memory", {}, "SQLite Persistent Knowledge & Preferences"),
    ("security", "audit_permissions", {}, "evaluate_payload", {"payload": "rm -rf /; echo evil"}, "Authorization Center & DPAPI Vault"),
    ("voice", "voice_status", {}, "invalid_voice", {}, "openWakeWord & Speech Synthesis Coordination"),
    ("vision", "vision_status", {}, "invalid_vision", {}, "AirTouch & MediaPipe Computer Vision"),
    ("repo_intel", "query_inventory", {}, "invalid_repo", {}, "Repository Capability & Tool Registry"),
    ("automation", "list_workflows", {}, "invalid_workflow", {}, "Scheduled Autonomous Task Cycles")
]

async def verify_all_agents():
    print("=" * 80)
    print("      MATRIX AI — ALL 16 SPECIALIZED AGENTS FULL LIFECYCLE AUDIT")
    print("=" * 80)

    results = []
    
    for agent_name, valid_action, valid_params, err_action, err_params, description in AGENTS_SUITE:
        print(f"\n--- Testing Agent: {agent_name.upper()} ({description}) ---")
        t0 = time.perf_counter()
        
        # 1. Discovery
        agent_instance = task_router.get_agent(agent_name)
        discovered = agent_instance is not None
        
        # 2. Capabilities
        caps = agent_instance.declare_capabilities() if (discovered and hasattr(agent_instance, "declare_capabilities")) else getattr(agent_instance, "_capabilities", [])
        has_caps = len(caps) > 0
        
        # 3. Authorization check
        can_run, profile, reason = authorization_center.evaluate_authorization(valid_action)
        
        # 4. Real Execution via TaskRouter
        res_exec = await task_router.dispatch(agent_name, valid_action, valid_params)
        exec_ok = res_exec.success and res_exec.execution_status in ("SUCCESS", "COMPLETED")
        
        # 5. Error Propagation via TaskRouter
        res_err = await task_router.dispatch(agent_name, err_action, err_params)
        err_ok = (not res_err.success) and (res_err.execution_status in ("FAILED", "BLOCKED"))
        
        total_ms = (time.perf_counter() - t0) * 1000
        
        all_passed = discovered and has_caps and exec_ok and err_ok
        status = "PASS" if all_passed else "FAIL"
        
        print(f"[{status:4}] {agent_name:15} | Discovery: {discovered} | Caps: {len(caps)} | Exec: {res_exec.execution_status} | Error Guard: {res_err.execution_status} ({total_ms:.1f}ms)")
        
        results.append({
            "agent": agent_name,
            "description": description,
            "status": status,
            "discovery": discovered,
            "capabilities_count": len(caps),
            "valid_action": valid_action,
            "exec_status": res_exec.execution_status,
            "exec_time_ms": res_exec.execution_time_ms,
            "error_action": err_action,
            "error_status": res_err.execution_status,
            "error_message": res_err.error,
            "duration_ms": round(total_ms, 2)
        })

    print("\n" + "=" * 80)
    passed_count = sum(1 for r in results if r["status"] == "PASS")
    print(f"ALL 16 AGENTS OUTCOME: {passed_count} / {len(results)} PASSED")
    print("=" * 80)

    out_file = Path(r"D:\matrix_data\reports\agents_full_lifecycle_audit.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps({
        "total_agents": len(results),
        "passed_agents": passed_count,
        "results": results
    }, indent=2), encoding="utf-8")
    print(f"Saved audit catalog to: {out_file}")

if __name__ == "__main__":
    asyncio.run(verify_all_agents())
