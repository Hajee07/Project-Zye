import sys
import json

sys.path.insert(0, r"d:\Zye")
from zye_windows.app_discovery import WindowsAppDiscovery

disc = WindowsAppDiscovery()
apps = disc.get_installed_apps()
print(f"Total apps in discovery: {len(apps)}")

targets = ["Chrome", "Google Chrome", "Word", "Excel", "PowerPoint", "WhatsApp", "Notepad", "Calculator"]
for t in targets:
    res = disc.search_installed_apps(t)
    if res:
        print(f"MATCH for '{t}': {res[0].application_name} (AppID: {res[0].app_id}, Type: {res[0].installation_type})")
    else:
        print(f"NO MATCH for '{t}'")
