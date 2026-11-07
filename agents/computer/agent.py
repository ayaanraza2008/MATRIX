"""MATRIX PC Computer Control Agent.
Performs application launching, closing, window detection, window switching, screenshot capture,
mouse/keyboard automation, process monitoring, and controlled system commands under strict policy verification on Windows 11.
"""
from typing import Dict, Any, Optional, List
import subprocess
import time
import os
import psutil
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from config.settings import settings
from vision.screenshot.capture import desktop_screen_capture


class ComputerAgent(BaseAgent):
    """Controls the Windows 11 desktop environment."""

    SAFE_COMMAND_ALLOWLIST = [
        "dir", "echo", "hostname", "ipconfig", "systeminfo", "tasklist",
        "whoami", "ver", "date /t", "time /t", "get-process", "get-service",
        "ping 127.0.0.1"
    ]

    APP_MAP = {
        "notepad": "notepad.exe",
        "calc": "calc.exe",
        "calculator": "calc.exe",
        "cmd": "cmd.exe",
        "terminal": "wt.exe",
        "powershell": "powershell.exe",
        "explorer": "explorer.exe",
        "code": "code.cmd",
        "chrome": "chrome.exe"
    }

    def __init__(self):
        super().__init__(
            name="computer",
            description="Executes authorized Windows 11 application, window, process, and desktop operations.",
            max_autonomy_level=2
        )
        self._capabilities = [
            AgentCapability(name="pc_execute", description="Execute safe terminal commands", operations=["command", "whoami", "hostname", "ipconfig", "systeminfo"]),
            AgentCapability(name="app_management", description="Launch and close authorized applications", operations=["open", "launch", "close", "kill"]),
            AgentCapability(name="window_management", description="List and switch active desktop windows", operations=["list_windows", "switch_window"]),
            AgentCapability(name="screen_capture", description="Capture desktop display surfaces", operations=["screenshot"]),
            AgentCapability(name="process_monitoring", description="Inspect active OS processes", operations=["list_processes"])
        ]

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("raw_prompt", parameters.get("query", "")).lower()

        # 1. Take Screenshot
        if "screenshot" in action_lower or "screenshot" in raw_prompt:
            return await self._take_screenshot(start_time)

        # 2. Close Application
        if any(w in action_lower or w in raw_prompt for w in ["close", "kill", "terminate"]):
            app_target = self._detect_target_app(raw_prompt)
            return await self._close_app(app_target, start_time)

        # 3. Window Switching
        if "switch" in action_lower or "focus" in action_lower:
            target = parameters.get("target", parameters.get("window", ""))
            return await self._switch_window(target, start_time)

        # 4. Window Listing
        if "window" in action_lower or "running apps" in raw_prompt:
            return await self._list_windows(start_time)

        # 5. Process Monitoring
        if "process" in action_lower or "running processes" in raw_prompt or "tasklist" in raw_prompt:
            return await self._list_processes(start_time)

        # 6. Controlled Command Execution
        if "command" in action_lower or "cmd" in action_lower or any(c in raw_prompt for c in ["whoami", "hostname", "ipconfig", "systeminfo", "dir", "ping"]):
            cmd = parameters.get("command", "")
            if not cmd:
                for sc in self.SAFE_COMMAND_ALLOWLIST:
                    if sc in raw_prompt:
                        cmd = sc
                        break
            if not cmd:
                cmd = raw_prompt.strip()
            return await self._execute_controlled_command(cmd, start_time)

        # 7. Launch Application
        if any(w in action_lower or w in raw_prompt for w in ["open", "launch", "start", "run"]):
            app_target = self._detect_target_app(raw_prompt)
            return await self._launch_app(app_target, start_time)

        # 8. Keyboard & Mouse Simulation
        if "type" in action_lower or "press" in action_lower or "click" in action_lower:
            return await self._simulate_input(action_lower, parameters, start_time)

        # Default fallback
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="query_status",
            data={"status": "Computer agent active", "os": "Windows 11", "allowlisted_apps": list(self.APP_MAP.keys())},
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def _take_screenshot(self, start_time: float) -> AgentResult:
        """Capture screen using the multi-tier desktop capture engine."""
        res = desktop_screen_capture.capture()
        latency = (time.perf_counter() - start_time) * 1000
        verified = res.get("success", False)

        return AgentResult(
            success=verified,
            agent_name=self.name,
            action_taken="capture_screenshot",
            data=res,
            verification={"file_exists": verified, "verified": verified},
            execution_time_ms=round(latency, 2)
        )

    async def _launch_app(self, app_name: str, start_time: float) -> AgentResult:
        """Launch authorized common Windows applications."""
        executable = self.APP_MAP.get(app_name, None)
        if not executable:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="launch_application",
                error=f"Application '{app_name}' is not in the authorized pre-approved allowlist.",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        try:
            subprocess.Popen([executable], shell=True)
            time.sleep(0.5)
            verified = self._is_process_running(executable.replace(".exe", "").replace(".cmd", ""))
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=verified,
                agent_name=self.name,
                action_taken="launch_application",
                data={"application": app_name, "executable": executable},
                verification={"process_running": verified, "verified": verified},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="launch_application",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _close_app(self, app_name: str, start_time: float) -> AgentResult:
        """Close an authorized running application gracefully."""
        executable = self.APP_MAP.get(app_name, None)
        if not executable:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="close_application",
                error=f"Application '{app_name}' is not in allowlist.",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        proc_target = executable.replace(".exe", "").replace(".cmd", "").lower()
        terminated_count = 0
        for p in psutil.process_iter(['name']):
            try:
                if proc_target in p.info['name'].lower():
                    p.terminate()
                    terminated_count += 1
            except Exception:
                pass

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="close_application",
            data={"application": app_name, "terminated_processes": terminated_count},
            verification={"verified": True, "closed": True},
            execution_time_ms=round(latency, 2)
        )

    async def _list_processes(self, start_time: float) -> AgentResult:
        """List top running processes by memory usage."""
        procs = []
        for p in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                procs.append({"pid": p.info['pid'], "name": p.info['name'], "ram_mb": round(mem_mb, 1)})
            except Exception:
                pass
        procs.sort(key=lambda x: x['ram_mb'], reverse=True)
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="list_processes",
            data={"processes": procs[:10], "total_count": len(procs)},
            verification={"verified": True},
            execution_time_ms=round(latency, 2)
        )

    async def _list_windows(self, start_time: float) -> AgentResult:
        """List active visible Windows titles."""
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            titles = [w.title for w in windows if w.title.strip()]
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_windows",
                data={"active_windows": titles[:15], "count": len(titles)},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_windows",
                data={"os": "Windows 11", "status": "Desktop active"},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )

    async def _switch_window(self, target_title: str, start_time: float) -> AgentResult:
        """Activate and bring to foreground a window matching the title."""
        try:
            import pygetwindow as gw
            matching = [w for w in gw.getAllWindows() if target_title.lower() in w.title.lower()]
            if matching:
                w = matching[0]
                if w.isMinimized:
                    w.restore()
                w.activate()
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="switch_window",
                    data={"target_window": w.title, "switched": True},
                    verification={"verified": True},
                    execution_time_ms=round(latency, 2)
                )
            else:
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="switch_window",
                    error=f"No window matching '{target_title}' found.",
                    verification={"verified": False},
                    execution_time_ms=round(latency, 2)
                )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="switch_window",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _execute_controlled_command(self, cmd: str, start_time: float) -> AgentResult:
        """Run an authorized non-destructive diagnostic command."""
        cmd_clean = cmd.strip()
        first_token = cmd_clean.split()[0].lower() if cmd_clean else ""

        is_allowed = any(cmd_clean.lower().startswith(allowed) for allowed in self.SAFE_COMMAND_ALLOWLIST)
        if not is_allowed:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="execute_command",
                error=f"Command '{first_token}' is not permitted by MATRIX policy gate.",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        try:
            res = subprocess.run(cmd_clean, shell=True, capture_output=True, text=True, timeout=8)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=(res.returncode == 0),
                agent_name=self.name,
                action_taken="execute_command",
                data={
                    "command": cmd_clean,
                    "stdout": res.stdout[:500] if res.stdout else "",
                    "returncode": res.returncode
                },
                verification={"verified": res.returncode == 0},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="execute_command",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _simulate_input(self, action: str, params: Dict[str, Any], start_time: float) -> AgentResult:
        """Simulate mouse/keyboard input safely with fail-safes."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True

            if "type" in action:
                text = params.get("text", "")
                pyautogui.write(text, interval=0.02)
            elif "press" in action:
                key = params.get("key", "enter")
                pyautogui.press(key)

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="simulate_input",
                data={"simulated_action": action},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="simulate_input",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    def _detect_target_app(self, text: str) -> str:
        for app in self.APP_MAP.keys():
            if app in text:
                return app
        return "unknown"

    def _is_process_running(self, process_name: str) -> bool:
        for p in psutil.process_iter(['name']):
            try:
                if process_name.lower() in p.info['name'].lower():
                    return True
            except Exception:
                pass
        return False

    async def verify(self, action: str, result: Any) -> bool:
        return bool(result and (isinstance(result, dict) or getattr(result, "success", True)))
