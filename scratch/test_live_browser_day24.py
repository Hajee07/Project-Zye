"""
Live End-to-End Test for Day 24 Browser Automation.
Launches persistent Chrome context in headless mode, navigates, takes DOM snapshot, and closes cleanly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from zye_browser import (
    BrowserLifecycleController,
    BrowserNavigationController,
    BrowserSessionManager,
    DOMContentExtractor,
    ProfileManager,
)


async def main():
    print("--- STARTING LIVE DAY 24 BROWSER TEST ---")
    pm = ProfileManager()

    # 1. Register test profile
    test_pid = "live_test_profile"
    p = pm.create_profile(
        profile_id=test_pid,
        display_name="Live Test Account",
        email="livetest@zye.local",
        aliases=["livetest"],
        tamil_aliases=["சோதனை"],
    )
    print(f"[1] Created persistent profile: {p.profile_id} at {p.user_data_dir}")

    # 2. Launch persistent session
    sm = BrowserSessionManager.get_instance(pm)
    lc = BrowserLifecycleController(sm, pm)
    print("[2] Launching browser session in headless mode...")
    status = await lc.start(account_query=test_pid, headless=True)
    print(f"[2] Browser launched. Version: {status.chrome_version}, Tabs: {status.tabs_count}")

    # 3. Navigate
    nc = BrowserNavigationController(sm)
    target_url = "https://example.com"
    print(f"[3] Navigating to {target_url}...")
    nav_res = await nc.navigate(target_url)
    print(f"[3] Navigated: title='{nav_res.get('title')}', url='{nav_res.get('current_url')}'")

    # 4. Extract DOM snapshot
    extractor = DOMContentExtractor(sm)
    print("[4] Extracting DOM snapshot...")
    snapshot = await extractor.extract_page_snapshot(max_chars=2000)
    print(f"[4] Extracted snapshot: {snapshot.character_count} chars, Headings: {snapshot.headings}")
    print(f"Content preview:\n{snapshot.content_text[:200]}...")

    # 5. Close session cleanly
    print("[5] Closing browser session...")
    close_res = await lc.stop()
    print(f"[5] Session closed: {close_res}")

    # 6. Delete test profile files
    pm.delete_profile(test_pid, delete_files=True)
    print(f"[6] Test profile cleaned up from disk.")

    print("--- LIVE DAY 24 BROWSER TEST COMPLETED SUCCESSFULLY ---")


if __name__ == "__main__":
    asyncio.run(main())
