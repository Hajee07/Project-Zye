import sys
import os
import asyncio
import traceback

sys.path.insert(0, r"d:\Zye")
import main

async def main_test():
    print("1. Creating agent...", flush=True)
    agent = main.ZyeMasterAgent()
    print("2. Calling _dispatch_tool_call('search_installed_apps', {'query': 'Chrome'})...", flush=True)
    try:
        res = await agent._dispatch_tool_call("search_installed_apps", {"query": "Chrome"}, timeout_seconds=5.0)
        print("3. Success! Result type:", type(res), flush=True)
        print("Result:", res, flush=True)
    except Exception as exc:
        print("Caught exception:", exc, flush=True)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main_test())
