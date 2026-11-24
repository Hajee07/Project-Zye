import sys
import time

print("STEP 1: Starting script", flush=True)
sys.path.insert(0, r"d:\Zye")
print("STEP 2: Path inserted", flush=True)

import main
print("STEP 3: main imported", flush=True)

agent = main.ZyeMasterAgent()
print("STEP 4: agent created", flush=True)

import asyncio
async def test():
    print("STEP 5: Inside test coroutine", flush=True)
    res = await agent._dispatch_tool_call("open_any_app", {"app_name": "calc", "timeout": 1.0})
    print("STEP 6: dispatch returned", flush=True)
    print("Result:", res, flush=True)

print("STEP 4.5: running loop", flush=True)
asyncio.run(test())
print("STEP 7: Done", flush=True)
