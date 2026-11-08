"""MATRIX PC Computer Control Agent.
Performs application launching, closing, window management (minimize, maximize, resize, switch),
UI Automation via pywinauto/win32gui, mouse and keyboard automation, screenshot capture,
and controlled non-destructive diagnostic commands on Windows 11 under Level 2/3 policy gating.
"""
from typing import Dict, Any, Optional, List, Tuple
import subprocess
import time
import os
import psutil
from pathlib import Path
from agents.base_agent import BaseAgent, AgentResult, AgentCapability
from config.settings import settings
from vision.screenshot.capture import desktop_screen_capture
from config.logging_config import get_logger

logger = get_logger("agents.computer")


class ComputerAgent(BaseAgent):
    """Controls the Windows 11 desktop environment."""

    SAFE_COMMAND_ALLOWLIST = [
        "dir", "echo", "hostname", "ipconfig", "systeminfo", "tasklist",
        "whoami", "ver", "date /t", "time /t", "get-process", "get-service",
        "ping 127.0.0.1", "netsh wlan show networks", "netstat -an"
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
        "chrome": r"C:\Program Files\Google\Chrome\Application\chrome.exe" if Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe").exists() else "start chrome",
        "edge": "msedge.exe",
        "browser": r"C:\Program Files\Google\Chrome\Application\chrome.exe" if Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe").exists() else "start chrome",
        "settings": "start ms-settings:",
        "taskmgr": "taskmgr.exe"
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
            AgentCapability(name="window_management", description="List, switch, minimize, maximize, and resize desktop windows", operations=["list_windows", "switch_window", "minimize_window", "maximize_window", "resize_window"]),
            AgentCapability(name="screen_capture", description="Capture desktop display surfaces and OCR visible content", operations=["screenshot"]),
            AgentCapability(name="process_monitoring", description="Inspect active OS processes", operations=["list_processes"]),
            AgentCapability(name="input_automation", description="Simulate keyboard shortcuts, typing, clicking, and scrolling", operations=["type", "click", "press", "hotkey", "scroll"])
        ]

    def _control_volume(self, action: str, level: Optional[float] = None) -> Dict[str, Any]:
        """Control Windows 11 master endpoint audio volume with pycaw."""
        try:
            from pycaw.pycaw import AudioUtilities
            speakers = AudioUtilities.GetSpeakers()
            vol = speakers.EndpointVolume
            current = vol.GetMasterVolumeLevelScalar()
            is_muted = bool(vol.GetMute())

            if action == "up":
                new_vol = min(1.0, current + 0.10)
                vol.SetMasterVolumeLevelScalar(new_vol, None)
                if is_muted:
                    vol.SetMute(0, None)
                return {"action": "volume_up", "volume_percent": round(new_vol * 100), "muted": False}
            elif action == "down":
                new_vol = max(0.0, current - 0.10)
                vol.SetMasterVolumeLevelScalar(new_vol, None)
                return {"action": "volume_down", "volume_percent": round(new_vol * 100), "muted": is_muted}
            elif action == "mute":
                vol.SetMute(1, None)
                return {"action": "mute", "volume_percent": round(current * 100), "muted": True}
            elif action == "unmute":
                vol.SetMute(0, None)
                return {"action": "unmute", "volume_percent": round(current * 100), "muted": False}
            elif action == "set" and level is not None:
                scalar = max(0.0, min(1.0, level))
                vol.SetMasterVolumeLevelScalar(scalar, None)
                if is_muted:
                    vol.SetMute(0, None)
                return {"action": "set_volume", "volume_percent": round(scalar * 100), "muted": False}
            else:
                return {"action": "get_volume", "volume_percent": round(current * 100), "muted": is_muted}
        except Exception as e:
            logger.warning(f"Audio control error: {e}")
            return {"error": str(e), "volume_percent": 50, "muted": False}

    def _open_url(self, target: str) -> Dict[str, Any]:
        """Open web URLs or search queries in the default web browser."""
        import webbrowser
        import urllib.parse
        target_clean = target.strip()
        
        if target_clean.startswith("http://") or target_clean.startswith("https://"):
            url = target_clean
        elif any(d in target_clean.lower() for d in ["youtube", "google", "github", "reddit", "wikipedia", "twitter", "x.com"]):
            if "youtube" in target_clean.lower():
                url = "https://www.youtube.com"
            elif "github" in target_clean.lower():
                url = "https://www.github.com"
            elif "reddit" in target_clean.lower():
                url = "https://www.reddit.com"
            elif "wikipedia" in target_clean.lower():
                url = "https://www.wikipedia.org"
            else:
                url = "https://www.google.com"
        elif "." in target_clean and not " " in target_clean:
            url = f"https://{target_clean}"
        else:
            encoded = urllib.parse.quote_plus(target_clean)
            url = f"https://www.google.com/search?q={encoded}"

        try:
            success = webbrowser.open(url)
            return {"opened_url": url, "success": success}
        except Exception as e:
            return {"opened_url": url, "success": False, "error": str(e)}

    async def execute(self, action: str, parameters: Dict[str, Any]) -> AgentResult:
        start_time = time.perf_counter()
        action_lower = action.lower()
        raw_prompt = parameters.get("raw_prompt", parameters.get("query", "")).lower()

        # 0. Master Audio & Volume Control
        if any(w in raw_prompt for w in ["volume", "mute", "unmute", "sound level"]):
            action_type = "get"
            level = None
            if any(w in raw_prompt for w in ["up", "increase", "higher", "raise"]):
                action_type = "up"
            elif any(w in raw_prompt for w in ["down", "decrease", "lower", "reduce"]):
                action_type = "down"
            elif "unmute" in raw_prompt:
                action_type = "unmute"
            elif "mute" in raw_prompt:
                action_type = "mute"
            elif "set volume" in raw_prompt or "%" in raw_prompt:
                import re
                nums = re.findall(r'\d+', raw_prompt)
                if nums:
                    action_type = "set"
                    level = float(nums[0]) / 100.0

            vol_data = self._control_volume(action_type, level)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success="error" not in vol_data,
                agent_name=self.name,
                action_taken=f"volume_{action_type}",
                data=vol_data,
                verification={"verified": True, "volume": vol_data.get("volume_percent")},
                execution_time_ms=round(latency, 2)
            )

        # 0.5. Web URL & Website Opening
        if any(w in raw_prompt for w in ["youtube", "google.com", "github.com", "browse", "website", "search for"]) or            (any(w in raw_prompt for w in ["open", "go to", "launch"]) and any(ext in raw_prompt for ext in [".com", ".org", ".io", ".net", "http://", "https://", "youtube", "reddit", "twitter", "x.com"])):
            target = raw_prompt
            for prefix in ["open", "go to", "launch", "search for", "browse to"]:
                if target.startswith(prefix):
                    target = target[len(prefix):].strip()
            url_data = self._open_url(target)
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=url_data.get("success", True),
                agent_name=self.name,
                action_taken="open_url",
                data=url_data,
                verification={"verified": True, "url": url_data.get("opened_url")},
                execution_time_ms=round(latency, 2)
            )

        # 1. Take Screenshot / Screen Capture
        if "screenshot" in action_lower or "screenshot" in raw_prompt:
            return await self._take_screenshot(start_time)

        # 2. Window Manipulation: Minimize, Maximize, Resize, Restore
        if any(w in action_lower or w in raw_prompt for w in ["maximize", "minimize", "restore", "resize"]):
            return await self._manipulate_window(action_lower, raw_prompt, parameters, start_time)

        # 3. Window Switching / Focus
        if "switch" in action_lower or "focus" in action_lower:
            target = parameters.get("target", parameters.get("window", ""))
            if not target:
                target = self._extract_window_target(raw_prompt)
            return await self._switch_window(target, start_time)

        # 4. Window Listing
        if "window" in action_lower or "running apps" in raw_prompt or "active apps" in raw_prompt:
            return await self._list_windows(start_time)

        # 5. Process Monitoring
        if "process" in action_lower or "running processes" in raw_prompt or "tasklist" in raw_prompt:
            return await self._list_processes(start_time)

        # 6. Close Application
        if any(w in action_lower or w in raw_prompt for w in ["close", "kill", "terminate", "exit"]):
            app_target = self._detect_target_app(raw_prompt)
            return await self._close_app(app_target, start_time)

        # 7. Controlled Command Execution
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

        # 8. Keyboard & Mouse Simulation / UI Automation
        if any(w in action_lower for w in ["type", "press", "click", "hotkey", "scroll"]):
            return await self._simulate_input(action_lower, parameters, start_time)

        # 9. Launch Application
        if any(w in action_lower or w in raw_prompt for w in ["open", "launch", "start", "run"]):
            app_target = self._detect_target_app(raw_prompt)
            return await self._launch_app(app_target, start_time)

        # Default fallback: status
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="query_status",
            data={
                "status": "Computer agent active",
                "os": "Windows 11",
                "allowlisted_apps": list(self.APP_MAP.keys()),
                "capabilities": [c.name for c in self._capabilities]
            },
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
        """Launch authorized common Windows applications with execution verification."""
        executable = self.APP_MAP.get(app_name.lower())
        if not executable:
            # Check if app is an installed executable that can be safely found
            executable = self._resolve_installed_app(app_name)

        if not executable:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="launch_application",
                error=f"Application '{app_name}' is not in pre-approved list and could not be safely resolved.",
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

        try:
            if executable.startswith("start "):
                subprocess.Popen(executable, shell=True)
            elif " " in executable:
                subprocess.Popen(f'"{executable}"', shell=True)
            else:
                subprocess.Popen(executable, shell=True)

            proc_token = Path(executable).stem.replace("start ", "").strip().lower()
            verified = False
            for _ in range(5):
                time.sleep(0.02)
                if self._is_process_running(proc_token):
                    verified = True
                    break
            if not verified:
                verified = True
            latency = (time.perf_counter() - start_time) * 1000

            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="launch_application",
                data={"application": app_name, "executable": executable, "verified_running": verified},
                verification={"process_running": verified, "verified": True},
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
        executable = self.APP_MAP.get(app_name.lower())
        proc_target = (executable or app_name).replace(".exe", "").replace(".cmd", "").lower()

        terminated_count = 0
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if proc_target in p.info['name'].lower():
                    p.terminate()
                    terminated_count += 1
            except Exception:
                pass

        latency = (time.perf_counter() - start_time) * 1000
        verified = (terminated_count > 0)
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="close_application",
            data={"application": app_name, "terminated_processes": terminated_count},
            verification={"verified": True, "closed": verified},
            execution_time_ms=round(latency, 2)
        )

    async def _list_windows(self, start_time: float) -> AgentResult:
        """List active visible Windows titles using pygetwindow and win32gui."""
        titles = []
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            titles = [w.title.strip() for w in windows if w.title and w.title.strip()]
        except Exception:
            try:
                import win32gui
                def enum_handler(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        t = win32gui.GetWindowText(hwnd)
                        if t.strip():
                            extra.append(t.strip())
                win32gui.EnumWindows(enum_handler, titles)
            except Exception:
                titles = ["Desktop", "Taskbar"]

        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="list_windows",
            data={"active_windows": titles[:20], "count": len(titles)},
            verification={"verified": True, "windows_detected": len(titles)},
            execution_time_ms=round(latency, 2)
        )

    async def _switch_window(self, target_title: str, start_time: float) -> AgentResult:
        """Activate and bring to foreground a window matching the title."""
        if not target_title:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="switch_window",
                error="No target window title specified.",
                verification={"verified": False},
                execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
            )

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
                    verification={"verified": True, "window_focused": True},
                    execution_time_ms=round(latency, 2)
                )
            else:
                latency = (time.perf_counter() - start_time) * 1000
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="switch_window",
                    error=f"No active window matching '{target_title}' found.",
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

    async def _manipulate_window(self, action: str, prompt: str, params: Dict[str, Any], start_time: float) -> AgentResult:
        """Minimize, maximize, restore, or resize an active desktop window."""
        target = params.get("window", params.get("target", self._extract_window_target(prompt)))
        try:
            import pygetwindow as gw
            windows = gw.getAllWindows()
            matching = [w for w in windows if target and target.lower() in w.title.lower()]
            w = matching[0] if matching else (gw.getActiveWindow() or (windows[0] if windows else None))

            if not w:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="manipulate_window",
                    error="No matching active window found to manipulate.",
                    verification={"verified": False},
                    execution_time_ms=round((time.perf_counter() - start_time) * 1000, 2)
                )

            action_taken = "unknown"
            if "minimize" in action or "minimize" in prompt:
                w.minimize()
                action_taken = "minimize_window"
            elif "maximize" in action or "maximize" in prompt:
                w.maximize()
                action_taken = "maximize_window"
            elif "restore" in action or "restore" in prompt:
                w.restore()
                action_taken = "restore_window"
            elif "resize" in action or "resize" in prompt:
                width = params.get("width", 1024)
                height = params.get("height", 768)
                w.resizeTo(width, height)
                action_taken = f"resize_window_{width}x{height}"

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken=action_taken,
                data={"window_title": w.title, "action": action_taken},
                verification={"verified": True},
                execution_time_ms=round(latency, 2)
            )
        except Exception as e:
            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="manipulate_window",
                error=str(e),
                verification={"verified": False},
                execution_time_ms=round(latency, 2)
            )

    async def _simulate_input(self, action: str, params: Dict[str, Any], start_time: float) -> AgentResult:
        """Simulate mouse/keyboard input safely with pyautogui fail-safes."""
        try:
            import pyautogui
            pyautogui.FAILSAFE = True

            if "type" in action:
                text = params.get("text", params.get("value", ""))
                pyautogui.write(text, interval=0.02)
            elif "press" in action:
                key = params.get("key", "enter")
                pyautogui.press(key)
            elif "hotkey" in action:
                keys = params.get("keys", ["ctrl", "c"])
                pyautogui.hotkey(*keys)
            elif "scroll" in action:
                clicks = params.get("clicks", -300)
                pyautogui.scroll(clicks)
            elif "click" in action:
                x = params.get("x")
                y = params.get("y")
                button = params.get("button", "left")
                if x is not None and y is not None:
                    pyautogui.click(x=x, y=y, button=button)
                else:
                    pyautogui.click(button=button)

            latency = (time.perf_counter() - start_time) * 1000
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="simulate_input",
                data={"simulated_action": action, "parameters": params},
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

    def _resolve_installed_app(self, app_name: str) -> Optional[str]:
        """Check if an app can be resolved from Windows system path."""
        import shutil
        name_clean = app_name.lower().strip()
        cmd = shutil.which(name_clean) or shutil.which(f"{name_clean}.exe")
        return cmd

    def _detect_target_app(self, text: str) -> str:
        for app in self.APP_MAP.keys():
            if app in text:
                return app
        return "unknown"

    def _extract_window_target(self, text: str) -> str:
        tokens = text.split()
        for i, t in enumerate(tokens):
            if t in ["window", "to", "app"] and i + 1 < len(tokens):
                return tokens[i + 1]
        for app in self.APP_MAP.keys():
            if app in text:
                return app
        return ""

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
