import sys
import asyncio
import time

sys.path.insert(0, r"d:\Zye")
import main

async def run():
    agent = main.ZyeMasterAgent()
    print("Testing dispatch open_any_app...")
    t0 = time.time()
    res = await agent._dispatch_tool_call("open_any_app", {"app_name": "calc", "timeout": 5.0})
    print(f"Result in {time.time() - t0:.2f}s:")
    print(res)

if __name__ == "__main__":
    asyncio.run(run())
