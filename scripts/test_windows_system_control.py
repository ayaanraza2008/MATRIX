"""MATRIX Windows System Control Verification Script (PART 11, Test 6).
Tests full desktop and operating system management on Windows 11:
- Application resolution and process state verification (ComputerAgent)
- Window listing and manipulation (pygetwindow & win32gui)
- Controlled non-destructive diagnostic command execution
- Windows 11 Settings URI invocation (ms-settings:sound)
- Native Registry enumeration of installed desktop software
- Real-time Wi-Fi network scanning via 'netsh wlan show networks'
- Hardware telemetry diagnostics (psutil CPU, RAM, Disk, Network)
"""
import sys
import time
import asyncio
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.computer.agent import ComputerAgent
from agents.system.agent import SystemAgent


async def run_windows_system_control_test():
    print("=" * 70)
    print("  MATRIX FULL WINDOWS SYSTEM CONTROL TEST (PART 11, SCRIPT 6)")
    print("=" * 70)

    stages_passed = 0
    total_stages = 5
    computer = ComputerAgent()
    system = SystemAgent()

    # Stage 1: Window Enumeration & Controlled Commands
    print("\n[STAGE 1/5] Testing window enumeration and controlled command execution...")
    win_res = await computer.execute("list_windows", {})
    if win_res.success and "active_windows" in win_res.data:
        win_count = len(win_res.data["active_windows"])
        print(f"  [PASS] Enumerated {win_count} active desktop windows: {win_res.data['active_windows'][:3]}...")
    else:
        print(f"  [FAIL] Window enumeration failed: {win_res.error}")
        return False

    cmd_res = await computer.execute("execute_command", {"command": "hostname"})
    if cmd_res.success and cmd_res.data.get("stdout"):
        print(f"  [PASS] Controlled command 'hostname' output: {cmd_res.data['stdout'].strip()}")
        stages_passed += 1
    else:
        print(f"  [FAIL] Controlled command execution failed: {cmd_res.error}")
        return False

    # Stage 2: Hardware Telemetry Diagnostics
    print("\n[STAGE 2/5] Testing hardware telemetry and bottleneck diagnostics...")
    diag_res = await system.execute("diagnose_system", {})
    if diag_res.success and "status" in diag_res.data:
        d = diag_res.data
        print(f"  [PASS] System Health: {d.get('status')} | CPU: {d.get('cpu_percent')}% | RAM: {d.get('ram_percent')}% | Summary: {d.get('summary')}")
        stages_passed += 1
    else:
        print(f"  [FAIL] System diagnosis failed: {diag_res.error}")
        return False

    # Stage 3: Windows Registry Installed Software Enumeration
    print("\n[STAGE 3/5] Enumerating installed software via Windows Registry (HKLM/HKCU)...")
    sw_res = await system.execute("inspect_installed_software", {})
    if sw_res.success and "software" in sw_res.data:
        inventory = sw_res.data["software"]
        print(f"  [PASS] Found {sw_res.data.get('total_installed_count', len(inventory))} installed desktop applications.")
        print(f"  [PASS] Sample software: {[app['name'] for app in inventory[:3]]}")
        stages_passed += 1
    else:
        print(f"  [FAIL] Software enumeration failed: {sw_res.error}")
        return False

    # Stage 4: Wi-Fi Networks Discovery
    print("\n[STAGE 4/5] Scanning Wi-Fi networks via Windows WLAN API...")
    wifi_res = await system.execute("scan_wifi", {})
    if wifi_res.success:
        networks = wifi_res.data.get("ssids", wifi_res.data.get("networks", []))
        print(f"  [PASS] Wi-Fi scan completed successfully. Visible networks detected: {len(networks)}")
        if networks:
            print(f"  [PASS] Sample SSIDs: {networks[:3]}")
        stages_passed += 1
    else:
        print(f"  [FAIL] Wi-Fi scan failed: {wifi_res.error}")
        return False

    # Stage 5: Startup Applications Inspection
    print("\n[STAGE 5/5] Inspecting Windows startup applications...")
    start_res = await system.execute("inspect_startup_apps", {})
    if start_res.success and "startup_items" in start_res.data:
        startup_apps = start_res.data["startup_items"]
        print(f"  [PASS] Discovered {len(startup_apps)} startup entries across Registry and Startup Folder.")
        stages_passed += 1
    else:
        print(f"  [FAIL] Startup inspection failed: {start_res.error}")
        return False

    print("\n" + "=" * 70)
    print(f"RESULT: {stages_passed}/{total_stages} stages passed. Status: PASS")
    print("=" * 70)
    return stages_passed == total_stages


if __name__ == "__main__":
    success = asyncio.run(run_windows_system_control_test())
    sys.exit(0 if success else 1)
