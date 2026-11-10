with open('agents/computer/agent.py', 'r') as f:
    content = f.read()

# Add _take_screenshot method before _list_processes
take_screenshot_method = '''
    def _take_screenshot(self, start_time: float) -> AgentResult:
        \"\"\"Capture a screenshot of the desktop.\"\"\"
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
'''

# Find the _list_processes method position and insert before it
list_processes_idx = content.find('def _list_processes')
if take_screenshot_idx := content.find('def _list_processes'):
    content = content[:take_screenshot_idx] + take_screenshot_method + content[take_screenshot_idx:]
    print('Added _take_screenshot method')

# Add _simulate_input method
simulate_input_method = '''
    def _simulate_input(self, action_lower: str, parameters: Dict[str, Any], start_time: float) -> AgentResult:
        \"\"\"Simulate keyboard input.\"\"\"
        import re
        raw_prompt = parameters.get("raw_prompt", parameters.get("query", "")).lower()
        
        # Extract text to type
        text_match = re.search(r'\"([^\"]+)\"', raw_prompt)
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
'''

# Insert before _list_processes
list_procs_idx = content.find('def _list_processes')
if list_procs_idx >= 0:
    content = content[:list_procs_idx] + simulate_input_method + content[list_procs_idx:]
    print('Added _simulate_input method')
else:
    print('Could not find _list_processes position')

# Write the file
with open('agents/computer/agent.py', 'w') as f:
    f.write(content)
print('Done adding methods')
PYEOF