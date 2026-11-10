import sys
sys.path.insert(0, r'C:\Users\Ali Raza Zaidi\Desktop\matrix')

# Read and execute the agent module directly
with open('agents/computer/agent.py', 'r') as f:
    code = f.read()

# Execute in a fresh namespace
namespace = {}
exec(code, namespace)

# Create agent instance
agent = namespace['ComputerAgent']()
print('Methods with list:', [m for m in dir(agent) if 'list' in m.lower()])
print('_list_processes in dir:', '_list_processes' in dir(agent))

# Test the _list_processes method
result = agent._list_processes(0.0)
print('Processes found:', result.data.get('count', 0))
print('First process:', result.data.get('processes', [])[0] if result.data else 'none')
PYEOF