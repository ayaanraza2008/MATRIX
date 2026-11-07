import json
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding='utf-8')

print("=== REPOSITORY INTELLIGENCE AUDIT ===")
inv_file = Path("starred_repos_inventory.json")
if not inv_file.exists():
    print("ERROR: starred_repos_inventory.json not found!")
    sys.exit(1)

with open(inv_file, 'r', encoding='utf-8') as f:
    repos = json.load(f)

print(f"Total Repositories in Inventory: {len(repos)}")

# Categories
cat_counts = {}
license_counts = {}
for r in repos:
    c = r.get("category", "Uncategorized")
    cat_counts[c] = cat_counts.get(c, 0) + 1
    lic = r.get("license") or "Unspecified"
    license_counts[lic] = license_counts.get(lic, 0) + 1

print("\n--- Categories Breakdown ---")
for c, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
    print(f"  {c:<30} : {cnt}")

print("\n--- Licenses Breakdown ---")
for lic, cnt in sorted(license_counts.items(), key=lambda x: -x[1]):
    print(f"  {lic:<30} : {cnt}")

# Check adapters in repository_engine
adapters_dir = Path("repository_engine/adapters")
adapters = list(adapters_dir.glob("*.py")) if adapters_dir.exists() else []
print(f"\n--- Adapters in repository_engine/adapters ({len(adapters)}) ---")
for a in adapters:
    print(f"  - {a.name}")

# Detailed check of which repos are adapted vs reference-only
adapted_names = [a.stem.replace("_adapter", "") for a in adapters]
print("\n--- Classification ---")
print(f"  - Adapted repositories with active bridges: {adapted_names}")
print(f"  - Reference & Evaluated Repositories: {len(repos) - len(adapted_names)}")
