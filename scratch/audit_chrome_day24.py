import os
import json

paths = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]
found_chrome = [p for p in paths if os.path.exists(p)]
print("Chrome exe found:", found_chrome)

local_state = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Local State")
print("Local State exists:", os.path.exists(local_state))
if os.path.exists(local_state):
    try:
        with open(local_state, "r", encoding="utf-8") as f:
            data = json.load(f)
            info_cache = data.get("profile", {}).get("info_cache", {})
            print("Discovered Chrome profiles count:", len(info_cache))
            for k, v in info_cache.items():
                print(f"  Folder: {k}, Name: {v.get('name')}, Email: {v.get('user_name')}")
    except Exception as e:
        print("Error reading Local State:", e)
