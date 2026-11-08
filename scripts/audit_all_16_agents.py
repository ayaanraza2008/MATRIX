"""MATRIX All 16 Agents & Registered Tools Deep Audit.
Inspects, exercises, and audits every tool across all 16 specialized agents:
1. computer
2. browser
3. research
4. coding
5. files
6. voice
7. vision
8. android
9. system
10. personal
11. automation
12. creative
13. memory
14. repo_intel
15. security
16. data_analysis

Categorizes each capability as PASS, FAIL, SIMULATED, BLOCKED, or NOT CONFIGURED.
"""
import asyncio
import time
import json
import sys
from pathlib import Path
from typing import Dict, Any, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.task_router import task_router
from agents.base_agent import AgentResult

AGENTS = [
    "computer", "browser", "research", "coding",
    "files", "voice", "vision", "android",
    "system", "personal", "automation", "creative",
    "memory", "repo_intel", "security", "data_analysis"
]

audit_results: Dict[str, Any] = {}

async def audit_agent(name: str):
    start = time.time()
    agent = task_router.get_agent(name)
    if not agent:
        return {
            "status": "FAIL",
            "import_ok": False,
            "error": f"Agent '{name}' not found in task_router registry"
        }

    tools_report = []

    # Safe test actions tailored per agent
    test_cases: List[Dict[str, Any]] = []

    if name == "computer":
        test_cases = [
            {"action": "get_volume", "params": {}},
            {"action": "list_processes", "params": {}},
            {"action": "whoami", "params": {}},
        ]
    elif name == "browser":
        test_cases = [
            {"action": "search_web", "params": {"query": "python asyncio"}},
            {"action": "navigate_url", "params": {"url": "https://httpbin.org/get"}},
        ]
    elif name == "research":
        test_cases = [
            {"action": "execute", "params": {"query": "quantum computing fundamentals"}},
            {"action": "deep_research", "params": {"query": "AMD Ryzen 5700U architecture"}},
        ]
    elif name == "coding":
        test_cases = [
            {"action": "validate_syntax", "params": {"code": "def hello():\n    return 'world'"}},
            {"action": "inspect_code_architecture", "params": {"file_path": "core/brain.py"}},
            {"action": "inspect_workspace", "params": {}},
        ]
    elif name == "files":
        test_cases = [
            {"action": "list_directory", "params": {"directory": "D:/matrix_data"}},
            {"action": "create_file", "params": {"filepath": "D:/matrix_data/test_audit.txt", "content": "MATRIX File Agent Audit"}},
            {"action": "get_metadata", "params": {"filepath": "D:/matrix_data/test_audit.txt"}},
        ]
    elif name == "voice":
        test_cases = [
            {"action": "synthesize_speech", "params": {"text": "Voice agent operational."}},
            {"action": "voice_control", "params": {"query": "status"}},
        ]
    elif name == "vision":
        test_cases = [
            {"action": "inspect_screen", "params": {}},
            {"action": "capture_screenshot", "params": {}},
        ]
    elif name == "android":
        test_cases = [
            {"action": "pair", "params": {}},
            {"action": "list_devices", "params": {}},
        ]
    elif name == "system":
        test_cases = [
            {"action": "poll_telemetry", "params": {}},
            {"action": "diagnose_system", "params": {}},
        ]
    elif name == "personal":
        test_cases = [
            {"action": "answer", "params": {"query": "Who are you?"}},
            {"action": "draft_email", "params": {"recipient": "test@example.com", "subject": "Test", "body": "Audit"}},
        ]
    elif name == "automation":
        test_cases = [
            {"action": "create_workflow", "params": {"title": "Audit Workflow", "steps": []}},
            {"action": "list_workflows", "params": {}},
        ]
    elif name == "creative":
        test_cases = [
            {"action": "generate_mermaid", "params": {"prompt": "Architecture diagram for Matrix AI"}},
        ]
    elif name == "memory":
        test_cases = [
            {"action": "save_memory", "params": {"key": "audit_test_key", "value": "matrix_audit_verified"}},
            {"action": "retrieve_memory", "params": {"key": "audit_test_key"}},
            {"action": "list_memory", "params": {}},
        ]
    elif name == "repo_intel":
        test_cases = [
            {"action": "query_inventory", "params": {"query": "voice"}},
            {"action": "list_capabilities", "params": {}},
        ]
    elif name == "security":
        test_cases = [
            {"action": "evaluate_payload", "params": {"command": "echo test"}},
            {"action": "audit_policy", "params": {}},
        ]
    elif name == "data_analysis":
        test_cases = [
            {"action": "data_status", "params": {}},
        ]

    for tc in test_cases:
        act = tc["action"]
        params = tc["params"]
        t0 = time.time()
        try:
            res: AgentResult = await agent.execute(act, params)
            elapsed = round((time.time() - t0) * 1000, 2)
            
            # Determine classification
            if res.success:
                cat = "PASS"
            elif "not configured" in (res.error or "").lower() or "missing api key" in (res.error or "").lower() or "credentials" in (res.error or "").lower():
                cat = "NOT CONFIGURED"
            elif "blocked" in (res.error or "").lower() or "unauthorized" in (res.error or "").lower():
                cat = "BLOCKED"
            elif "simulated" in (res.error or "").lower() or getattr(res, "simulated", False):
                cat = "SIMULATED"
            else:
                cat = "FAIL"

            tools_report.append({
                "action": act,
                "classification": cat,
                "success": res.success,
                "latency_ms": elapsed,
                "error": res.error,
                "data_keys": list(res.data.keys()) if isinstance(res.data, dict) else type(res.data).__name__
            })
        except Exception as ex:
            elapsed = round((time.time() - t0) * 1000, 2)
            tools_report.append({
                "action": act,
                "classification": "FAIL",
                "success": False,
                "latency_ms": elapsed,
                "error": str(ex),
                "data_keys": []
            })

    # Cleanup audit test file if created
    test_f = Path("D:/matrix_data/test_audit.txt")
    if test_f.exists():
        try:
            test_f.unlink()
        except Exception:
            pass

    return {
        "agent": name,
        "import_ok": True,
        "class_name": agent.__class__.__name__,
        "description": agent.description,
        "max_autonomy_level": agent.max_autonomy_level,
        "capabilities_count": len(agent.capabilities) if hasattr(agent, "capabilities") else 0,
        "tools_audited": tools_report,
        "total_time_ms": round((time.time() - start) * 1000, 2)
    }

async def run_full_audit():
    print("=" * 70)
    print("MATRIX COMPREHENSIVE 16-AGENT ARCHITECTURAL AUDIT")
    print("=" * 70)

    summary = {"total_agents": len(AGENTS), "passed_agents": 0, "tools_pass": 0, "tools_not_configured": 0, "tools_fail": 0, "tools_blocked": 0, "tools_simulated": 0}
    agent_reports = {}

    for name in AGENTS:
        print(f"Auditing agent: [{name}]...", end=" ", flush=True)
        res = await audit_agent(name)
        agent_reports[name] = res
        all_ok = all(t["classification"] in ("PASS", "NOT CONFIGURED") for t in res.get("tools_audited", []))
        if all_ok and res.get("import_ok"):
            summary["passed_agents"] += 1
            print("OK")
        else:
            print("WARNING/FAIL")

        for t in res.get("tools_audited", []):
            cat = t["classification"]
            if cat == "PASS":
                summary["tools_pass"] += 1
            elif cat == "NOT CONFIGURED":
                summary["tools_not_configured"] += 1
            elif cat == "BLOCKED":
                summary["tools_blocked"] += 1
            elif cat == "SIMULATED":
                summary["tools_simulated"] += 1
            else:
                summary["tools_fail"] += 1

    report_payload = {
        "timestamp": time.time(),
        "summary": summary,
        "agents": agent_reports
    }

    report_path = Path("D:/matrix_data/reports/agent_audit_results.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report_payload, indent=2), encoding="utf-8")
    print("\n" + "=" * 70)
    print(f"AUDIT COMPLETE: {summary['passed_agents']}/{summary['total_agents']} Agents Validated")
    print(f"Tools -> PASS: {summary['tools_pass']} | NOT CONFIGURED: {summary['tools_not_configured']} | BLOCKED: {summary['tools_blocked']} | FAIL: {summary['tools_fail']}")
    print(f"Saved audit log: {report_path}")
    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(run_full_audit())
