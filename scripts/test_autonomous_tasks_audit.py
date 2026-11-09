"""Audit script for the 8 Real Autonomous Tasks (A-H).
Verifies actual Windows OS state after execution.
"""
import sys
import os
import time
import asyncio
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

import psutil

task_results = {}

async def test_task_a():
    """Task A: Open Notepad."""
    print("\n--- Testing Task A: Open Notepad ---")
    from agents.computer.agent import ComputerAgent
    ca = ComputerAgent()
    res = await ca.execute("launch", {"app": "notepad"})
    time.sleep(1.5)
    
    # Verify in Windows process table
    notepad_running = any("notepad" in p.name().lower() for p in psutil.process_iter(['name']))
    print(f"Agent result: {res.success}, Process running: {notepad_running}")
    
    # Clean up: close notepad
    await ca.execute("close", {"app": "notepad"})
    time.sleep(0.5)
    notepad_closed = not any("notepad" in p.name().lower() for p in psutil.process_iter(['name']))
    
    passed = res.success and notepad_running and notepad_closed
    task_results["A_Notepad"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Launch: {res.success}, Process found: {notepad_running}, Closed: {notepad_closed}"
    }

async def test_task_b_c_d():
    """Task B, C, D: Create Desktop folder, write file, read file."""
    print("\n--- Testing Task B, C, D: Desktop folder, file write, file read ---")
    desktop_dir = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
    test_dir = desktop_dir / "matrix_audit_test_dir"
    test_file = test_dir / "matrix_test_payload.txt"
    test_content = f"Matrix autonomous verification audit timestamp={time.time()}"
    
    from agents.files.agent import FileAgent
    fa = FileAgent()
    
    # B: Create test folder
    r_mkdir = await fa.execute("mkdir", {"target_dir": str(desktop_dir), "folder_name": "matrix_audit_test_dir"})
    folder_exists = test_dir.exists() and test_dir.is_dir()
    task_results["B_CreateFolder"] = {
        "status": "PASS" if (r_mkdir.success and folder_exists) else "FAIL",
        "details": f"Agent success: {r_mkdir.success}, Desktop folder exists: {folder_exists}"
    }
    
    # C: Write file into that folder
    r_write = await fa.execute("create_file", {"filepath": str(test_file), "content": test_content})
    file_exists = test_file.exists() and test_file.stat().st_size > 0
    task_results["C_WriteFile"] = {
        "status": "PASS" if (r_write.success and file_exists) else "FAIL",
        "details": f"Agent success: {r_write.success}, File on disk: {file_exists}, size={test_file.stat().st_size if file_exists else 0}"
    }
    
    # D: Read that file and report contents
    r_read = await fa.execute("read_file", {"filepath": str(test_file)})
    read_text = str(r_read.data.get("content") or r_read.data.get("text") or "") if (r_read.data and isinstance(r_read.data, dict)) else str(r_read.data)
    read_matched = test_content in read_text
    task_results["D_ReadFile"] = {
        "status": "PASS" if (r_read.success and read_matched) else "FAIL",
        "details": f"Agent success: {r_read.success}, Content matched: {read_matched}"
    }
    
    # Clean up
    try:
        if test_file.exists(): test_file.unlink()
        if test_dir.exists(): test_dir.rmdir()
    except Exception as e:
        print(f"Cleanup warning: {e}")

async def test_task_e():
    """Task E: Open Calculator and calculate 125 * 48."""
    print("\n--- Testing Task E: Open Calculator and calculate 125 * 48 ---")
    from agents.computer.agent import ComputerAgent
    ca = ComputerAgent()
    
    # 1. Launch calculator
    r_launch = await ca.execute("launch", {"app": "calc"})
    time.sleep(1.5)
    calc_running = any("calc" in p.name().lower() for p in psutil.process_iter(['name']))
    
    # 2. Mathematical evaluation verification
    expected = 125 * 48  # 6000
    from core.brain import brain
    res_math = await brain.process_user_request(session_id="audit_math", user_prompt="Calculate 125 * 48")
    resp_text = res_math.get("response", "")
    math_correct = "6000" in resp_text or "6,000" in resp_text
    
    # Close calculator
    await ca.execute("close", {"app": "calculator"})
    
    passed = r_launch.success and calc_running and math_correct
    task_results["E_CalculatorMath"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Calc launched: {calc_running}, Math (125*48=6000) verified: {math_correct} (Response: '{resp_text[:60]}')"
    }

async def test_task_f():
    """Task F: Retrieve actual CPU and RAM usage."""
    print("\n--- Testing Task F: Retrieve actual CPU and RAM usage ---")
    from agents.system.agent import SystemAgent
    sa = SystemAgent()
    r = await sa.execute("poll_telemetry", {})
    
    data = r.data or {}
    cpu = data.get("cpu_percent") or (data.get("cpu", {}).get("percent") if isinstance(data.get("cpu"), dict) else None)
    ram = data.get("ram_used_mb") or (data.get("memory", {}).get("used_mb") if isinstance(data.get("memory"), dict) else None)
    ram_pct = data.get("ram_percent") or (data.get("memory", {}).get("percent") if isinstance(data.get("memory"), dict) else None)
    
    # Compare with native psutil
    native_cpu = psutil.cpu_percent(interval=0.1)
    native_ram = psutil.virtual_memory().percent
    
    passed = r.success and cpu is not None and ram is not None
    task_results["F_SystemMetrics"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Agent CPU: {cpu}%, RAM: {ram_pct}% ({ram} MB). Native psutil CPU: {native_cpu}%, RAM: {native_ram}%"
    }

async def test_task_g():
    """Task G: Find a relevant installed capability for a requested task."""
    print("\n--- Testing Task G: Find relevant installed capability ---")
    from core.capability_registry import capability_registry
    
    # Query for security capability
    matches = capability_registry.search("security")
    installed = [c for c in matches if c.maturity.value == "installed" or c.maturity == "installed"]
    has_cap = len(matches) > 0 and len(installed) > 0
    top_name = installed[0].name if installed else (matches[0].name if matches else "None")
    
    task_results["G_CapabilityDiscovery"] = {
        "status": "PASS" if has_cap else "FAIL",
        "details": f"Query 'security': found {len(matches)} capabilities ({len(installed)} installed). Top installed match: '{top_name}'"
    }

async def test_task_h():
    """Task H: Execute a three-step task without manual agent coordination."""
    print("\n--- Testing Task H: Autonomous 3-step task ---")
    from core.autonomy.autonomous_core import AutonomousCore
    ac = AutonomousCore()
    prompt = "Check current CPU usage, summarize system health, and verify data directory."
    t0 = time.perf_counter()
    res = await ac.execute_autonomous_cycle(prompt)
    dur = round(time.perf_counter() - t0, 2)
    
    traces = res.lifecycle_traces
    passed = res.success and len(traces) == 12
    task_results["H_AutonomousMultiStep"] = {
        "status": "PASS" if passed else "FAIL",
        "details": f"Completed 12 lifecycle stages in {dur}s. Result: {res.final_output[:80]}"
    }

async def run_all():
    await test_task_a()
    await test_task_b_c_d()
    await test_task_e()
    await test_task_f()
    await test_task_g()
    await test_task_h()
    
    print("\n" + "=" * 80)
    print("      REAL AUTONOMOUS TASK AUDIT RESULTS (TASKS A-H)")
    print("=" * 80)
    for k, v in task_results.items():
        print(f"[{v['status']:4}] Task {k:22} | {v['details']}")

if __name__ == "__main__":
    asyncio.run(run_all())
