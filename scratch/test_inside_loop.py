import sys
import asyncio

print("STEP 1: Starting script", flush=True)
sys.path.insert(0, r"d:\Zye")
import main

async def test():
    print("STEP 2: Inside test coroutine", flush=True)
    agent = main.ZyeMasterAgent()
    print("STEP 3: agent created inside loop", flush=True)
    res = await agent._dispatch_tool_call("open_any_app", {"app_name": "calc", "timeout": 1.0})
    print("STEP 4: dispatch returned", flush=True)
    print("Result:", res, flush=True)

asyncio.run(test())
print("STEP 5: Done", flush=True)
