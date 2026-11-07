import sys
import os
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path.cwd()))
sys.stdout.reconfigure(encoding='utf-8')

from core.task_router import task_router
from database.init_db import init_database

print("=== INDEPENDENT AUDIT: ALL 16 MATRIX AGENTS ===")

async def run_audit():
    # Ensure database is initialized
    await init_database()

    results_table = []
    
    # Define individual real tasks for each of the 16 agents
    tests = [
        ("1. computer", "computer", "list_windows", {"raw_prompt": "list active windows"}),
        ("2. browser", "browser", "navigate_url", {"url": "https://news.ycombinator.com"}),
        ("3. research", "research", "web_research", {"query": "FastAPI async Python"}),
        ("4. coding", "coding", "validate_syntax", {"instruction": "validate", "code": "def calculate_telemetry(x, y):\n    return x + y\n"}),
        ("5. files", "files", "list_storage_files", {}),
        ("6. voice", "voice", "speak", {"text": "Agent audit verification online."}),
        ("7. vision", "vision", "inspect_screen", {}),
        ("8. android", "android", "generate_pairing_token", {}),
        ("9. system", "system", "poll_telemetry", {}),
        ("10. personal", "personal", "personal_assist", {"query": "Identify current operating profile"}),
        ("11. automation", "automation", "create_workflow", {"title": "Audit Multi-Agent Lifecycle", "steps": ["observe", "plan", "verify"]}),
        ("12. creative", "creative", "render_media_plan", {"prompt": "JARVIS Holographic HUD UI"}),
        ("13. memory", "memory", "save_memory", {"key": "audit_run_id", "value": {"test": "16_agents", "status": "active"}}),
        ("14. repo_intel", "repo_intel", "query_inventory", {"query": "agent"}),
        ("15. security", "security", "evaluate_payload", {"command": "dir D:\\matrix_data"}),
        ("16. data_analysis", "data_analysis", "analyze_csv", {"csv_path": ""})
    ]

    # Pre-create test CSV for data analysis agent
    audit_dir = Path("D:/matrix_data/audit")
    audit_dir.mkdir(parents=True, exist_ok=True)
    sample_csv = audit_dir / "sample_metrics.csv"
    with open(sample_csv, "w", encoding="utf-8") as f:
        f.write("metric_id,latency_ms,ram_mb,score\n")
        f.write("1,12.5,850,92.0\n")
        f.write("2,14.1,865,95.5\n")
        f.write("3,9.8,840,89.0\n")
        f.write("4,15.2,890,98.2\n")
        f.write("5,11.3,855,91.5\n")
    tests[-1] = ("16. data_analysis", "data_analysis", "analyze_csv", {"csv_path": str(sample_csv)})

    for label, agent_name, action, params in tests:
        t0 = time.perf_counter()
        try:
            res = await task_router.dispatch(agent_name=agent_name, action=action, parameters=params)
            latency = (time.perf_counter() - t0) * 1000
            success = res.success
            status = "VERIFIED" if success else "FAILED"
            summary = str(res.data)[:90] if res.data else str(res.error)[:90]
            print(f"[{status}] {label:<20} | Time: {latency:6.1f}ms | Action: {res.action_taken}")
            print(f"       Data: {summary}")
            results_table.append({
                "agent": agent_name,
                "label": label,
                "status": status,
                "action": res.action_taken,
                "latency_ms": round(latency, 2),
                "evidence": summary,
                "verified": res.verification.get("verified", False) if res.verification else False
            })
        except Exception as e:
            latency = (time.perf_counter() - t0) * 1000
            print(f"[FAILED]   {label:<20} | Time: {latency:6.1f}ms | Exception: {e}")
            results_table.append({
                "agent": agent_name,
                "label": label,
                "status": "FAILED",
                "action": action,
                "latency_ms": round(latency, 2),
                "evidence": f"Exception: {e}",
                "verified": False
            })

    # Extra security tests: evaluate dangerous command blocking
    print("\n--- Testing Security Gate Dangerous Command Blocking ---")
    sec_agent = task_router.get_agent("security")
    res_danger = await sec_agent.execute("evaluate_payload", {"command": "rmdir /s /q C:\\Windows\\System32"})
    print(f"Dangerous command test: 'rmdir /s /q C:\\Windows\\System32'")
    print(f"  Result success (safe): {res_danger.success}")
    print(f"  Reason: {res_danger.data.get('reason')}")
    print(f"  Gate Blocked Correctly: {not res_danger.success}")

    # Extra files sandbox test: path traversal
    print("\n--- Testing Files Agent Path Traversal Protection ---")
    file_agent = task_router.get_agent("files")
    res_traversal = await file_agent.execute("read_file", {"filepath": "../../../windows/win.ini"})
    print(f"Path traversal test: '../../../windows/win.ini'")
    print(f"  Result success: {res_traversal.success}")
    print(f"  Error message: {res_traversal.error}")
    print(f"  Traversal Blocked Correctly: {not res_traversal.success}")

    total = len(results_table)
    passed = sum(1 for r in results_table if r["status"] == "VERIFIED")
    print(f"\n=== SUMMARY: {passed}/{total} AGENTS VERIFIED ===")

asyncio.run(run_audit())
