import sys
import time

sys.path.insert(0, r"d:\Zye")
from zye_windows.app_launcher import WindowsAppLauncher

print("Creating launcher...", flush=True)
launcher = WindowsAppLauncher()

print("Calling open_any_app('calc')...", flush=True)
t0 = time.time()
res = launcher.open_any_app("calc", timeout=5.0)
print(f"Result in {time.time() - t0:.2f}s: {res}", flush=True)
