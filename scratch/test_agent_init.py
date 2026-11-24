import sys
import time

print("1. Importing sys and time", flush=True)
sys.path.insert(0, r"d:\Zye")

t0 = time.time()
print("2. Importing main...", flush=True)
import main
print(f"2b. Main imported in {time.time() - t0:.2f}s", flush=True)

t0 = time.time()
print("3. Instantiating ZyeMasterAgent...", flush=True)
agent = main.ZyeMasterAgent()
print(f"3b. ZyeMasterAgent instantiated in {time.time() - t0:.2f}s", flush=True)
