import httpx
import json

api_key = "org_6c881cc9d9b66e97b11b6c8863fc372b0ba143984e48c73542463c1d5ffb78340f6f57ae415132c2422969"
headers = {"authorization": api_key}

client = httpx.Client(timeout=10.0)

# 1. Check account
r = client.get("https://api.bland.ai/v1/me", headers=headers)
print("Account details (/v1/me):", r.status_code)
print(json.dumps(r.json(), indent=2))

# 2. Check voices
r = client.get("https://api.bland.ai/v1/voices", headers=headers)
voices = r.json().get("voices", [])
print(f"Total voices: {len(voices)}")
for v in voices[:10]:
    print(f"  {v.get('name')}: {v.get('description')} (id: {v.get('id')})")
