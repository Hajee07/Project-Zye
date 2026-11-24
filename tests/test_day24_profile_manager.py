"""
Unit and Integration Tests for Persistent Profile Management — Day 24.
Covers path validation, lock management, Local State discovery, registry persistence, and Tamil/English account disambiguation.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from zye_browser.account_selector import AccountSelector
from zye_browser.browser_errors import (
    BrowserProfileError,
    BrowserProfileLockedError,
    BrowserProfileNotFoundError,
)
from zye_browser.models import BrowserProfileMetadata, DiscoveredChromeProfile
from zye_browser.profile_discovery import ChromeProfileDiscovery
from zye_browser.profile_lock_manager import ProfileLockManager
from zye_browser.profile_manager import ProfileManager
from zye_browser.profile_path_validator import ProfilePathValidator
from zye_browser.profile_registry import ProfileRegistry


class TestProfilePathValidator(unittest.TestCase):
    """Tests for ProfilePathValidator security controls."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_val_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_valid_profile_ids(self):
        self.assertEqual(ProfilePathValidator.validate_profile_id("personal"), "personal")
        self.assertEqual(ProfilePathValidator.validate_profile_id("work_account"), "work_account")
        self.assertEqual(ProfilePathValidator.validate_profile_id("profile-123"), "profile-123")

    def test_invalid_profile_ids_rejected(self):
        with self.assertRaises(BrowserProfileError):
            ProfilePathValidator.validate_profile_id("")

        with self.assertRaises(BrowserProfileError):
            ProfilePathValidator.validate_profile_id("invalid/slash")

        with self.assertRaises(BrowserProfileError):
            ProfilePathValidator.validate_profile_id("invalid\\backslash")

        with self.assertRaises(BrowserProfileError):
            ProfilePathValidator.validate_profile_id("../traversal")

    def test_path_traversal_prevention(self):
        resolved = ProfilePathValidator.resolve_profile_dir("work", self.temp_dir)
        self.assertEqual(resolved.parent, self.temp_dir)
        self.assertEqual(resolved.name, "profile_work")


class TestProfileLockManager(unittest.TestCase):
    """Tests for profile locking and concurrency protections."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_lock_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_acquire_and_release_lock(self):
        p_dir = self.temp_dir / "profile_test"
        p_dir.mkdir(parents=True)

        self.assertFalse(ProfileLockManager.is_profile_locked(p_dir))

        # Acquire lock
        ProfileLockManager.acquire_lock("test", p_dir)
        self.assertTrue(ProfileLockManager.is_profile_locked(p_dir))

        # Release lock
        ProfileLockManager.release_lock("test", p_dir)
        self.assertFalse(ProfileLockManager.is_profile_locked(p_dir))

    def test_clean_stale_locks(self):
        p_dir = self.temp_dir / "profile_stale"
        p_dir.mkdir(parents=True)

        zye_lock = p_dir / ".zye_lock"
        zye_lock.write_text("999999:stale_profile", encoding="utf-8")

        cleared = ProfileLockManager.clean_stale_locks(p_dir)
        self.assertTrue(cleared)
        self.assertFalse(zye_lock.exists())


class TestProfileRegistry(unittest.TestCase):
    """Tests for ProfileRegistry CRUD and synchronization."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_reg_test_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_register_and_get_profile(self):
        reg_file = self.temp_dir / "registry.json"
        reg = ProfileRegistry(registry_file=reg_file, profiles_root=self.temp_dir)

        p = reg.register_profile(
            profile_id="office",
            display_name="Work Office",
            email="work@company.com",
            aliases=["work", "office", "corp"],
            tamil_aliases=["வேலை", "ஆபீஸ்"],
        )

        self.assertEqual(p.profile_id, "office")
        self.assertEqual(p.display_name, "Work Office")
        self.assertEqual(p.email, "work@company.com")

        fetched = reg.get_profile("office")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.display_name, "Work Office")

    def test_sync_from_host_chrome(self):
        reg = ProfileRegistry(profiles_root=self.temp_dir)
        mock_discovered = [
            DiscoveredChromeProfile(
                chrome_profile_dir="Default",
                name="Personal Chrome",
                email="user@gmail.com",
            ),
            DiscoveredChromeProfile(
                chrome_profile_dir="Profile 2",
                name="Office Account",
                email="office.work@gmail.com",
            ),
        ]

        synced = reg.sync_from_host_chrome(mock_discovered)
        self.assertEqual(len(synced), 2)
        self.assertEqual(len(reg.list_profiles()), 2)

        office_p = reg.get_profile("profile_2")
        self.assertIsNotNone(office_p)
        self.assertIn("work", office_p.tags)
        self.assertIn("வேலை", office_p.tamil_aliases)


class TestAccountSelector(unittest.TestCase):
    """Tests for Tamil, English, and Tanglish account disambiguation."""

    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="zye_sel_test_"))
        self.reg = ProfileRegistry(profiles_root=self.temp_dir)
        self.reg.register_profile(
            profile_id="work",
            display_name="Office Work",
            email="employee@corp.com",
            aliases=["office", "work", "job", "officela"],
            tamil_aliases=["வேலை", "ஆபீஸ்"],
        )
        self.reg.register_profile(
            profile_id="personal",
            display_name="Personal Account",
            email="me.personal@gmail.com",
            aliases=["personal", "home"],
            tamil_aliases=["சொந்தம்", "பர்சனல்"],
        )
        self.reg.register_profile(
            profile_id="zyren",
            display_name="Zyren Bot Account",
            email="gptzyren@gmail.com",
            aliases=["zyren", "bot"],
            tamil_aliases=["சைரன்"],
        )
        self.selector = AccountSelector(self.reg)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_english_exact_match(self):
        res = self.selector.resolve("work")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.profile_id, "work")

    def test_english_alias_match(self):
        res = self.selector.resolve("open office account")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.profile_id, "work")

    def test_email_match(self):
        res = self.selector.resolve("employee@corp.com")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.profile_id, "work")

    def test_tamil_alias_match(self):
        res = self.selector.resolve("வேலை ஜிமெயில் திற")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.profile_id, "work")
        self.assertEqual(res.match_strategy, "tamil_alias_match")

    def test_tanglish_alias_match(self):
        res = self.selector.resolve("officela search pannu")
        self.assertTrue(res.matched)
        self.assertEqual(res.profile.profile_id, "work")

    def test_ambiguous_account_prompt(self):
        res = self.selector.resolve(None)
        self.assertFalse(res.matched)
        self.assertEqual(len(res.candidates), 3)
        self.assertIsNotNone(res.selection_prompt)
        self.assertIn("கணக்குகள்", res.selection_prompt)
        self.assertIn("accounts", res.selection_prompt.lower())


if __name__ == "__main__":
    unittest.main()
