import sys

sys.path.insert(0, r"d:\Zye")
from zye_windows.app_launcher import WindowsAppLauncher

launcher = WindowsAppLauncher()

for name in ["Chrome", "Google Chrome", "Word", "Excel", "PowerPoint", "WhatsApp", "Notepad"]:
    matches = launcher.discovery.search_installed_apps(name)
    print(f"Query '{name}': {len(matches)} matches -> {[m.application_name for m in matches]}")
