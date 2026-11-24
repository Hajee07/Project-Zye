import sys
import asyncio
import time

sys.path.insert(0, r"d:\Zye")
import main

async def run():
    t0 = time.time()
    agent = main.ZyeMasterAgent()
    print(f"Agent init: {time.time() - t0:.2f}s", flush=True)
    t1 = time.time()
    res = await agent._dispatch_tool_call("open_any_app", {"app_name": "calc", "timeout": 1.0})
    print(f"Tool call: {time.time() - t1:.2f}s", flush=True)
    print("Result:", res)

if __name__ == "__main__":
    asyncio.run(run())
