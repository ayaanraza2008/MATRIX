with open('agents/computer/agent.py', 'r') as f:
    content = f.read()

# Add _list_processes method before the verify method
new_method = '''
    def _list_processes(self, start_time: float) -> AgentResult:
        \"\"\"List all running processes on the system.\"\"\"
        try:
            processes = []
            for p in psutil.process_iter(['name', 'pid']):
                try:
                    processes.append({\"pid\": p.info[\"pid\"], \"name\": p.info[\"name\"]})
                except:
                    pass
            return AgentResult(
                success=True,
                agent_name=self.name,
                action_taken=\"list_processes\",
                data={\"processes\": processes, \"count\": len(processes)}
            )
        except ImportError:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken=\"list_processes\",
                error=\"psutil not available\"
            )
        except Exception as e:
            return AgentResult(
                success=False,
                agent_name=self.name,
                action_taken=\"list_processes\",
                error=str(e)
            )
'''

# Insert before the verify method
verify_idx = content.find('async def verify')
if verify_idx >= 0:
    content = content[:verify_idx] + new_method + content[verify_idx:]
    with open('agents/computer/agent.py', 'w') as f:
        f.write(content)
    print('Added _list_processes method')
else:
    print('Could not find verify method position')