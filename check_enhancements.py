
# Read the computer agent
with open('agents/computer/agent.py', 'r') as f:
    content = f.read()

# Check for enhanced methods
enhanced_methods = [
    '_simulate_click',
    '_simulate_double_click', 
    '_simulate_right_click',
    '_simulate_scroll',
    '_switch_window_alt_tab',
    '_list_open_windows',
    '_get_active_window',
    '_monitor_system_resources'
]

print('Enhanced method existence check:')
for method in enhanced_methods:
    if f'def {method}' in content:
        print(f'  [OK] {method} exists')
    else:
        print(f'  [MISSING] {method}')

print()
print('Key capability check:')
checks = ['_simulate_input', '_launch_app', '_close_app', '_list_windows', '_list_processes']
for check in checks:
    if f'def {check}' in content:
        print(f'  [OK] {check} exists')
    else:
        print(f'  [MISSING] {check}')