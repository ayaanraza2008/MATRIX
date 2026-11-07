import json
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

with open('starred_repos_inventory.json', 'r', encoding='utf-8') as f:
    repos = json.load(f)

print(f"Total: {len(repos)}")
for idx, r in enumerate(repos, 1):
    desc = (r.get("description") or "").replace("\n", " ")[:65]
    print(f"{idx:2d}. {r['full_name']:<38} | {str(r.get('language')):<12} | {str(r.get('stars')):<6} | {desc}")
