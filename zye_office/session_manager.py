"""
Live Office Session Manager — Zye Day 20.
Tracks active Office sessions, binds metadata without serializing raw COM objects,
persists session states to data/office_session_metadata.json, and handles disconnection detection.
"""

from __future__ import annotations

import json
import logging
import pathlib
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from zye_office.com_runtime import OfficeCOMRuntime
from zye_office.models import ConnectionPolicy, OfficeSessionMetadata, SessionStatus

logger = logging.getLogger("zye.office.session_manager")

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
SESSION_METADATA_FILE = DATA_DIR / "office_session_metadata.json"


class OfficeSessionManager:
    """
    Coordinates multi-application Office session metadata and state tracking.
    """

    def __init__(
        self,
        com_runtime: Optional[OfficeCOMRuntime] = None,
        metadata_file: Optional[pathlib.Path] = None,
    ) -> None:
        self.com_runtime = com_runtime or OfficeCOMRuntime()
        self.metadata_file = metadata_file or SESSION_METADATA_FILE
        self._sessions: dict[str, OfficeSessionMetadata] = {}  # session_id -> metadata
        self._app_to_session_id: dict[str, str] = {}  # norm_app -> session_id
        self._active_session_id: Optional[str] = None
        self._load_metadata_from_disk()

    def _load_metadata_from_disk(self) -> None:
        """Load stored session metadata if present on disk."""
        if not self.metadata_file.exists():
            return
        try:
            with open(self.metadata_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                meta = OfficeSessionMetadata(**item)
                # On startup, mark previous sessions as IDLE/DISCONNECTED
                meta.session_status = SessionStatus.DISCONNECTED
                self._sessions[meta.session_id] = meta
                self._app_to_session_id[meta.app_name.lower()] = meta.session_id
        except Exception as exc:
            logger.warning("Could not load session metadata from disk: %s", exc)

    def _save_metadata_to_disk(self) -> None:
        """Persist session metadata list atomically to disk."""
        try:
            self.metadata_file.parent.mkdir(parents=True, exist_ok=True)
            payload = [s.model_dump() for s in self._sessions.values()]
            tmp = self.metadata_file.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            tmp.replace(self.metadata_file)
        except Exception as exc:
            logger.warning("Could not persist session metadata to disk: %s", exc)

    @property
    def metadata_path(self) -> str:
        return str(self.metadata_file)

    def get_session(self, session_id: str) -> Optional[OfficeSessionMetadata]:
        """Lookup by session_id or app_name."""
        if session_id in self._sessions:
            return self._sessions[session_id]
        norm = session_id.lower().strip()
        if norm in self._app_to_session_id:
            sid = self._app_to_session_id[norm]
            return self._sessions.get(sid)
        return None

    def list_sessions(self) -> list[OfficeSessionMetadata]:
        return list(self._sessions.values())

    def touch_session(self, session_id: str) -> None:
        sess = self.get_session(session_id)
        if sess:
            sess.last_accessed_at = datetime.now(timezone.utc).isoformat()
            self._save_metadata_to_disk()

    def create_office_session(
        self,
        app_name: str,
        policy: ConnectionPolicy = ConnectionPolicy.ATTACH_EXISTING,
    ) -> dict[str, Any]:
        """
        Establish a live connection to an Office application and record session metadata.
        """
        norm_app = app_name.lower().strip()
        conn_res = self.com_runtime.connect_office_application(norm_app, policy=policy)
        if conn_res.get("status") != "SUCCESS":
            return conn_res

        # Reuse existing session or create fresh ID
        session_id = self._app_to_session_id.get(norm_app) or f"sess_{norm_app}_{uuid.uuid4().hex[:8]}"

        meta = OfficeSessionMetadata(
            session_id=session_id,
            app_name=norm_app,
            prog_id=conn_res.get("prog_id", ""),
            connection_policy=policy,
            is_saved=True,
            is_read_only=False,
            session_status=SessionStatus.ACTIVE,
            created_by_zye=conn_res.get("created_by_zye", False),
        )

        self._sessions[session_id] = meta
        self._app_to_session_id[norm_app] = session_id
        self._active_session_id = session_id
        self._save_metadata_to_disk()

        return {
            "status": "SUCCESS",
            "session_id": session_id,
            "app_name": norm_app,
            "connection_type": conn_res.get("connection_type"),
            "session_status": meta.session_status.value,
            "created_by_zye": meta.created_by_zye,
            "message": f"Active session established for {norm_app.title()}.",
        }

    def get_office_session(self, app_name: str) -> Optional[OfficeSessionMetadata]:
        """Retrieve session metadata for a given application."""
        norm_app = app_name.lower().strip()
        sess_id = self._app_to_session_id.get(norm_app)
        if sess_id:
            return self._sessions.get(sess_id)
        return None

    def get_active_office_session(self) -> Optional[OfficeSessionMetadata]:
        """Retrieve the currently focused/active Office session metadata."""
        if self._active_session_id:
            return self._sessions.get(self._active_session_id)
        return None

    def get_office_session_details(self, session_id: str) -> dict[str, Any]:
        """Get full details for a session by ID, verifying live COM responsiveness."""
        meta = self._sessions.get(session_id)
        if not meta:
            return {"status": "NOT_FOUND", "message": f"Session '{session_id}' not found."}

        # Verify live COM object status
        ver_res = self.com_runtime.verify_office_connection(meta.app_name)
        if not ver_res.get("is_connected", False):
            meta.session_status = SessionStatus.DISCONNECTED
            self._save_metadata_to_disk()

        res = meta.model_dump()
        res["status"] = "SUCCESS"
        res["is_live_connected"] = ver_res.get("is_connected", False)
        return res

    def refresh_office_session(self, session_id: str) -> dict[str, Any]:
        """Verify and refresh session timestamp and live state."""
        meta = self._sessions.get(session_id)
        if not meta:
            return {"status": "NOT_FOUND", "message": f"Session '{session_id}' not found."}

        ver_res = self.com_runtime.verify_office_connection(meta.app_name)
        if ver_res.get("is_connected"):
            meta.session_status = SessionStatus.ACTIVE
            meta.last_accessed_at = datetime.now(timezone.utc).isoformat()
        else:
            meta.session_status = SessionStatus.DISCONNECTED

        self._save_metadata_to_disk()
        return {
            "status": "SUCCESS",
            "session_id": session_id,
            "session_status": meta.session_status.value,
            "is_connected": ver_res.get("is_connected", False),
        }

    def close_office_session(self, session_id: str) -> dict[str, Any]:
        """Terminate session and release COM references."""
        meta = self._sessions.get(session_id)
        if not meta:
            return {"status": "NOT_FOUND", "message": f"Session '{session_id}' not found."}

        norm_app = meta.app_name.lower()
        self.com_runtime.disconnect_office_application(norm_app, quit_if_created_by_zye=meta.created_by_zye)
        meta.session_status = SessionStatus.DISCONNECTED
        self._app_to_session_id.pop(norm_app, None)
        if self._active_session_id == session_id:
            self._active_session_id = None

        self._save_metadata_to_disk()
        return {
            "status": "SUCCESS",
            "session_id": session_id,
            "app_name": norm_app,
            "message": f"Session '{session_id}' closed.",
        }
