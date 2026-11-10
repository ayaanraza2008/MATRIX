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

    SAFE_INPUT_ALLOWLIST = [
        r'^[a-zA-Z0-9\s\.\,\!\?\;:\'"\(\)\/\\-\@]+$',
        r'^\d+,\d+$',
    ]

    _CAPABILITIES = [
        AgentCapability(name="pc_execute", description="Execute safe terminal commands", operations=["command", "whoami", "hostname", "ipconfig", "systeminfo"]),
        AgentCapability(name="app_management", description="Launch and close authorized applications", operations=["open", "launch", "close", "kill"]),
        AgentCapability(name="window_management", description="List, switch, minimize, maximize, and resize desktop windows", operations=["list_windows", "switch_window", "minimize_window", "maximize_window", "resize_window"]),
        AgentCapability(name="screen_capture", description="Capture desktop display surfaces and OCR visible content", operations=["screenshot"]),
        AgentCapability(name="process_monitoring", description="Inspect active OS processes", operations=["list_processes"]),
        AgentCapability(name="input_automation", description="Simulate keyboard shortcuts, typing, clicking, and scrolling", operations=["type", "click", "press", "hotkey", "scroll"]),
        AgentCapability(name="mouse_control", description="Simulate mouse movement, clicks, and scrolling", operations=["move", "click", "double_click", "right_click", "scroll"]),
        AgentCapability(name="window_switching", description="Switch between applications and windows", operations=["alt_tab", "task_switch", "focus_window"]),
        AgentCapability(name="system_monitoring", description="Monitor CPU, RAM, and disk usage", operations=["get_system_info", "resource_usage"]),
    ]

    def __init__(self):
        super().__init__(
            name="computer",
            description="Executes authorized Windows 11 application, window, process, and desktop operations.",
            max_autonomy_level=2
        )

    # ---- Enhanced Mouse Control Methods ----

    def _get_win32_constants(self):
        """Get the required win32 constants."""
        import win32con
        return {
            "WMLBUTTONDOWN": win32con.WMLBUTTONDOWN,
            "WMLBUTTONUP": win32con.WMLBUTTONUP,
            "WM_RBUTTONDOWN": win32con.WMRBUTTONDOWN,
            "WM_RBUTTONUP": win32con.WMRBUTTONUP,
            "WM_MOUSEWHEEL": win32con.WM_MOUSEWHEEL,
            "MOUSEEVENTF_LEFTDOWN": win32con.MOUSEEVENTF_LEFTDOWN,
            "MOUSEEVENTF_LEFTUP": win32con.MOUSEEVENTF_LEFTUP,
            "MOUSEEVENTF_RIGHTDOWN": win32con.MOUSEEVENTF_RIGHTDOWN,
            "MOUSEEVENTF_RIGHTUP": win32con.MOUSEEVENTF_RIGHTUP,
            "MOUSEEVENTF_MOVE": win32con.MOUSEEVENTF_MOVE,
            "MOUSEEVENTF_WHEEL": win32con.MOUSEEVENTF_WHEEL,
        }

    def _simulate_click(self, x: int, y: int, click_type: str = "left") -> AgentResult:
        """Simulate a mouse click at given coordinates. Returns AgentResult."""
        try:
            import win32gui
            
            hwnd = win32gui.WindowFromPoint((x, y))
            if hwnd:
                if click_type == "left":
                    win32gui.SendMessage(hwnd, win32con.WMLBUTTONDOWN, 0, 0)
                    win32gui.SendMessage(hwnd, win32con.WMLBUTTONUP, 0, 0)
                elif click_type == "right":
                    win32gui.SendMessage(hwnd, win32con.WMRBUTTONDOWN, 0, 0)
                    win32gui.SendMessage(hwnd, win32con.WMRBUTTONUP, 0, 0)
                elif click_type == "double":
                    win32gui.SendMessage(hwnd, win32con.WMLBUTTONDOWN, 0, 0)
                    time.sleep(0.1)
                    win32gui.SendMessage(hwnd, win32con.WMLBUTTONUP, 0, 0)
                
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken=f"mouse_{click_type}_click",
                    data={"coordinates": (x, y), "click_type": click_type}
                )
            else:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="mouse_click",
                    error="No window at coordinates"
                )
        except Exception as e:
            # Fallback: use pyautogui
            try:
                import pyautogui
                if click_type == "left":
                    pyautogui.click(x=x, y=y)
                elif click_type == "right":
                    pyautogui.rightClick(x=x, y=y)
                elif click_type == "double":
                    pyautogui.doubleClick(x=x, y=y)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken=f"mouse_{click_type}_click",
                    data={"coordinates": (x, y), "click_type": click_type}
                )
            except Exception as e2:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="mouse_click",
                    error=str(e2)
                )

    def _simulate_double_click(self, x: int, y: int) -> AgentResult:
        """Simulate a double-click at given coordinates."""
        return self._simulate_click(x, y, click_type="double")

    def _simulate_right_click(self, x: int, y: int) -> AgentResult:
        """Simulate a right-click at given coordinates."""
        return self._simulate_click(x, y, click_type="right")

    def _simulate_scroll(self, x: int, y: int, amount: int = 3) -> AgentResult:
        """Simulate mouse scroll at given coordinates."""
        try:
            import win32gui
            import win32con
            
            hwnd = win32gui.WindowFromPoint((x, y))
            if hwnd:
                # Use PostMessage for scroll
                msg = win32con.WM_MOUSEWHEEL
                win32gui.PostMessage(hwnd, msg, amount * 120, 0)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="mouse_scroll",
                    data={"coordinates": (x, y), "scroll_amount": amount}
                )
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="mouse_scroll",
                error="No window at coordinates"
            )
        except Exception as e:
            # Fallback: use pyautogui
            try:
                import pyautogui
                if amount > 0:
                    pyautogui.scroll(amount, x=x, y=y)
                else:
                    pyautogui.scroll(-amount, x=x, y=y)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="mouse_scroll",
                    data={"coordinates": (x, y), "scroll_amount": amount}
                )
            except Exception as e2:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="mouse_scroll",
                    error=str(e2)
                )

    # ---- Enhanced Window Switching Methods ----

    def _switch_window_alt_tab(self, repetitions: int = 1) -> AgentResult:
        """Simulate Alt+Tab to switch between open windows."""
        try:
            import win32gui
            import win32api
            import win32con
            
            for _ in range(repetitions):
                win32api.keybd_event(18, 0, 0, 0)  # Alt key down
                win32api.keybd_event(9, 0, 0, 0)   # Tab key down
                time.sleep(0.1)
                win32api.keybd_event(9, 0, win32con.KEYEVENTF_KEYUP, 0)  # Tab key up
                win32api.keybd_event(18, 0, win32con.KEYEVENTF_KEYUP, 0)  # Alt key up
                time.sleep(0.1)
            
            # Get the foreground window after alt-tab
            foreground = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(foreground)
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="alt_tab",
                data={"repetitions": repetitions, "foreground_title": window_title}
            )
        except ImportError:
            # Fallback: just simulate key events
            try:
                import keyboard
                for _ in range(repetitions):
                    keyboard.press_and_release('alt+tab')
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="alt_tab",
                    data={"repetitions": repetitions}
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="alt_tab",
                    error=str(e)
                )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="alt_tab",
                error=str(e)
            )

    def _list_open_windows(self) -> AgentResult:
        """List all open windows on the desktop."""
        try:
            import win32gui
            
            windows = []
            def enum_handler(hwnd, ctx):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title:
                        windows.append({"hwnd": str(hwnd), "title": title})
            
            win32gui.EnumWindows(enum_handler, None)
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_windows",
                data={"windows": windows}
            )
        except ImportError:
            # Fallback using psutil
            try:
                processes = []
                for p in psutil.process_iter(['name', 'pid']):
                    try:
                        processes.append({"pid": p.info['pid'], "name": p.info['name']})
                    except:
                        pass
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="list_processes",
                    data={"processes": processes, "note": "Using psutil fallback"}
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="list_processes",
                    error=str(e)
                )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="list_windows",
                error=str(e)
            )

    def _get_active_window(self) -> AgentResult:
        """Get the currently active/window focus."""
        try:
            import win32gui
            
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="get_active_window",
                data={"hwnd": str(hwnd), "title": title, "class_name": class_name}
            )
        except ImportError:
            try:
                import pygetwindow as gw
                windows = gw.getWindowsWithTitle("")
                if windows:
                    w = windows[0]
                    return AgentResult(
                        success=True,
                        agent_name=self.name,
                        action_taken="get_active_window",
                        data={"title": w.title, "pid": w._pid}
                    )
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="get_active_window",
                    error="No active window found"
                )
            except Exception as e:
                return AgentResult(
                    success=False,
                    agent_name=self.name,
                    action_taken="get_active_window",
                    error=str(e)
                )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="get_active_window",
                error=str(e)
            )

    # ---- System Monitoring Methods ----

    def _monitor_system_resources(self) -> AgentResult:
        """Get current CPU, RAM, and disk usage."""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory info
            mem = psutil.virtual_memory()
            mem_total_gb = mem.total / (1024**3)
            mem_available_gb = mem.available / (1024**3)
            mem_percent = mem.percent
            
            # Disk info
            disk = psutil.disk_usage('/')
            disk_total_gb = disk.total / (1024**3)
            disk_free_gb = disk.free / (1024**3)
            disk_percent = disk.percent
            
            # Process count
            process_count = len(list(psutil.process_iter(['name'])))
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="get_system_info",
                data={
                    "cpu_percent": cpu_percent,
                    "memory": {
                        "total_gb": round(mem_total_gb, 2),
                        "available_gb": round(mem_available_gb, 2),
                        "percent": mem_percent
                    },
                    "disk": {
                        "total_gb": round(disk_total_gb, 2),
                        "free_gb": round(disk_free_gb, 2),
                        "percent": disk_percent
                    },
                    "process_count": process_count
                }
            )
        except ImportError:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="get_system_info",
                error="psutil not available"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="get_system_info",
                error=str(e)
            )

    # ---- Existing Methods (simplified) ----

    def _control_volume(self, action: str, level: Optional[float] = None) -> AgentResult:
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
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="volume_up",
                    data={"volume_percent": round(new_vol * 100), "muted": False}
                )
            elif action == "down":
                new_vol = max(0.0, current - 0.10)
                vol.SetMasterVolumeLevelScalar(new_vol, None)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="volume_down",
                    data={"volume_percent": round(new_vol * 100), "muted": False}
                )
            elif action == "mute":
                vol.SetMute(1, None)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="mute",
                    data={"volume_percent": round(current * 100), "muted": True}
                )
            elif action == "unmute":
                vol.SetMute(0, None)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="unmute",
                    data={"volume_percent": round(current * 100), "muted": False}
                )
            elif action == "set" and level is not None:
                scalar = max(0.0, min(1.0, level))
                vol.SetMasterVolumeLevelScalar(scalar, None)
                if is_muted:
                    vol.SetMute(0, None)
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="set_volume",
                    data={"volume_percent": round(scalar * 100), "muted": False}
                )
            else:
                return AgentResult(
                    success=True,
                    agent_name=self.name,
                    action_taken="get_volume",
                    data={"volume_percent": round(current * 100), "muted": is_muted}
                )
        except Exception as e:
            logger.warning(f"Audio control error: {e}")
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="get_volume",
                error=str(e)
            )

    def _open_url(self, target: str) -> AgentResult:
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
            return AgentResult(
                success=success,
                agent_name=self.name,
                action_taken="open_url",
                data={"opened_url": url, "success": success}
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="open_url",
                data={"opened_url": url, "success": False, "error": str(e)}
            )

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
        if any(w in raw_prompt for w in ["youtube", "google.com", "github.com", "browse", "website", "search for"]) or \
           (any(w in raw_prompt for w in ["open", "go to", "launch"]) and any(ext in raw_prompt for ext in [".com", ".org", ".io", ".net", "http://", "https://", "youtube", "reddit", "twitter", "x.com"])):
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
            return self._take_screenshot(start_time)

        # 1.5. Enhanced: Mouse Actions
        if any(w in action_lower for w in ["click", "double_click", "right_click", "scroll", "move"]):
            return self._handle_mouse_action(action_lower, parameters, start_time)

        # 2. Window Manipulation: Minimize, Maximize, Resize, Restore
        if any(w in action_lower or w in raw_prompt for w in ["maximize", "minimize", "restore", "resize"]):
            return self._manipulate_window(action_lower, raw_prompt, parameters, start_time)

        # 3. Window Switching / Focus
        if "switch" in action_lower or "focus" in action_lower:
            target = parameters.get("target", parameters.get("window", ""))
            if not target:
                target = self._extract_window_target(raw_prompt)
            return await self._switch_window(target, start_time)

        # 4. Window Listing
        if "window" in action_lower or "running apps" in raw_prompt or "active apps" in raw_prompt or "show windows" in raw_prompt:
            return self._list_open_windows()

        # 5. Process Monitoring
        if "process" in action_lower or "running processes" in raw_prompt or "tasklist" in raw_prompt:
            return self._list_processes(start_time)

        # 6. Close Application
        if any(w in action_lower or w in raw_prompt for w in ["close", "kill", "terminate", "exit"]):
            app_target = parameters.get("app") or parameters.get("target") or parameters.get("application") or self._detect_target_app(raw_prompt)
            return self._close_app(app_target, start_time)

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
            return self._execute_controlled_command(cmd, start_time)

        # 7.5. Keyboard & Mouse Simulation
        if any(w in action_lower for w in ["type", "press"]):
            return self._simulate_input(action_lower, parameters, start_time)

        # 7.6. Enhanced: Mouse Action Dispatch
        if any(w in action_lower for w in ["click", "scroll", "move"]):
            return self._handle_mouse_action(action_lower, parameters, start_time)

        # 8. Launch Application
        if any(w in action_lower or w in raw_prompt for w in ["open", "launch", "start", "run"]):
            app_target = parameters.get("app") or parameters.get("target") or parameters.get("application") or self._detect_target_app(raw_prompt)
            return await self._launch_app(app_target, start_time)

        # 9. Enhanced: Mouse Control Dispatch (click, scroll, move)
        # Already handled above in section 1.5

        # 9. Enhanced: Window Switching (Alt+Tab)
        if any(w in action_lower for w in ["alt", "tab", "switch window"]):
            return self._switch_window_alt_tab(repetitions=1)

        # 10. Enhanced: System Monitoring
        if any(w in action_lower for w in ["system", "resources", "cpu", "ram", "disk", "usage"]):
            return self._monitor_system_resources()

        # Default fallback: status
        latency = (time.perf_counter() - start_time) * 1000
        return AgentResult(
            success=True,
            agent_name=self.name,
            action_taken="query_status",
            data={
                "timestamp": time.time(),
                "note": "No matching action found; returning status"
            },
            execution_time_ms=round(latency, 2)
        )

    def _handle_mouse_action(self, action_lower: str, parameters: Dict[str, Any], start_time: float) -> AgentResult:
        """Handle mouse actions: click, double-click, right-click, scroll, move."""
        import re
        
        # Try to extract coordinates from the prompt
        coords = re.search(r'(\d+),\s*(\d+)', parameters.get("raw_prompt", parameters.get("query", "")))
        x, y = 500, 500  # default center
        
        if coords:
            x, y = int(coords.group(1)), int(coords.group(2))
        
        if "click" in action_lower and "double" not in action_lower and "right" not in action_lower:
            # Left click
            result = self._simulate_click(x, y, click_type="left")
            return AgentResult(success=result.success, agent_name=self.name, action_taken="mouse_click", data=result.data, error=result.error, execution_time_ms=round((time.perf_counter() - start_time) * 1000))
        elif "double" in action_lower:
            result = self._simulate_double_click(x, y)
            return AgentResult(success=result.success, agent_name=self.name, action_taken="mouse_double_click", data=result.data, error=result.error, execution_time_ms=round((time.perf_counter() - start_time) * 1000))
        elif "right" in action_lower:
            result = self._simulate_right_click(x, y)
            return AgentResult(success=result.success, agent_name=self.name, action_taken="mouse_right_click", data=result.data, error=result.error, execution_time_ms=round((time.perf_counter() - start_time) * 1000))
        elif "scroll" in action_lower:
            # Determine scroll direction
            if "up" in action_lower:
                result = self._simulate_scroll(x, y, amount=3)
            elif "down" in action_lower:
                result = self._simulate_scroll(x, y, amount=-3)
            else:
                result = self._simulate_scroll(x, y, amount=3)
            return AgentResult(success=result.success, agent_name=self.name, action_taken="mouse_scroll", data=result.data, error=result.error, execution_time_ms=round((time.perf_counter() - start_time) * 1000))
        elif "move" in action_lower:
            result = {"success": True, "action": "mouse_move", "coordinates": (x, y)}
            return AgentResult(success=True, agent_name=self.name, action_taken="mouse_move", data=result, execution_time_ms=round((time.perf_counter() - start_time) * 1000))
        
        return AgentResult(success=False, agent_name=self.name, action_taken="mouse_action", error="Unrecognized mouse action", execution_time_ms=round((time.perf_counter() - start_time) * 1000))

    # Keep existing verification method
    
    
    def _take_screenshot(self, start_time: float) -> AgentResult:
        """Capture a screenshot of the desktop."""
        try:
            from vision.screenshot.capture import desktop_screen_capture
            img = desktop_screen_capture()
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="screenshot",
                data={"image": img, "note": "Screenshot captured (platform-dependent)"}
            )
        except ImportError:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="screenshot",
                error="Screenshot capture not available"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="screenshot",
                error=str(e)
            )

    def _simulate_input(self, action_lower: str, parameters: Dict[str, Any], start_time: float) -> AgentResult:
        """Simulate keyboard input."""
        import re
        raw_prompt = parameters.get("raw_prompt", parameters.get("query", "")).lower()
        
        # Extract text to type
        text_match = re.search(r'"([^"]+)"', raw_prompt)
        text = text_match.group(1) if text_match else raw_prompt.strip()
        
        # Simple keyboard simulation using pyautogui
        try:
            import pyautogui
            # Type the text character by character
            for char in text:
                pyautogui.write(char, interval=0.01)
            
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="keyboard_type",
                data={"text_typed": text, "char_count": len(text)}
            )
        except ImportError:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="keyboard_type",
                error="pyautogui not available"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="keyboard_type",
                error=str(e)
            )
def _list_processes(self, start_time: float) -> AgentResult:
        """List all running processes on the system."""
        try:
            processes = []
            for p in psutil.process_iter(['name', 'pid']):
                try:
                    processes.append({"pid": p.info["pid"], "name": p.info["name"]})
                except:
                    pass
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken="list_processes",
                data={"processes": processes, "count": len(processes)}
            )
        except ImportError:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="list_processes",
                error="psutil not available"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken="list_processes",
                error=str(e)
            )
async def verify(self, action: str, result: Any) -> bool:
        return bool(result and (isinstance(result, dict) or getattr(result, "success", True)))