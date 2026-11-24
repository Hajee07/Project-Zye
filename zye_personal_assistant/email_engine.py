"""
Email Management Intelligence Engine for Zye Personal Assistant (Day 14 & Day 29).
Provides secure IMAP4_SSL unread retrieval with BODY.PEEK[], intelligent priority triage,
local draft storage, SMTP_SSL sending with Negative Brain audit and confirmation gating.
Audit logging to logs/email_audit.log and SQLite email_action_history.
"""

from __future__ import annotations

import email
from email.header import decode_header
import email.message
import imaplib
import logging
import os
import re
import smtplib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Tuple

from zye_personal_assistant.database import get_db_connection, init_assistant_database
from zye_personal_assistant.safety_gateway import SafetyGateway

logger = logging.getLogger("zye.personal_assistant.email")

# Dedicated email audit logger
_AUDIT_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_AUDIT_LOG_FILE = _AUDIT_LOG_DIR / "email_audit.log"
_AUDIT_LOG_DIR.mkdir(parents=True, exist_ok=True)

_email_audit_logger = logging.getLogger("zye.email_audit")
if not _email_audit_logger.handlers:
    _fh = logging.FileHandler(_AUDIT_LOG_FILE, encoding="utf-8")
    _fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    _email_audit_logger.addHandler(_fh)
    _email_audit_logger.setLevel(logging.INFO)

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

PRIORITY_KEYWORDS = {
    "CRITICAL": {
        "keywords": ["urgent", "emergency", "immediate action", "server down", "production outage", "critical security", "security alert"],
        "reason": "Security emergency, server outage, or immediate action required",
    },
    "HIGH": {
        "keywords": ["invoice", "payment", "deadline", "client meeting", "contract", "approval needed", "blocker", "action required", "statement"],
        "reason": "Client response, urgent invoice, payment, or important project deadline",
    },
    "LOW": {
        "keywords": ["newsletter", "digest", "promotion", "marketing", "webinar", "notification", "sale", "deals", "discount"],
        "reason": "Newsletter, promotional digest, or informational marketing content",
    },
    "MEDIUM": {
        "keywords": ["update", "status", "feedback", "review", "weekly report", "follow-up", "summary"],
        "reason": "Standard correspondence or routine project update",
    },
}

PRIORITY_RANK = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


def _decode_mime_words(val: str | bytes | None) -> str:
    """Decode RFC 2047 MIME encoded words safely."""
    if not val:
        return ""
    if isinstance(val, bytes):
        val = val.decode("utf-8", errors="replace")
    decoded_fragments: list[str] = []
    try:
        for fragment, encoding in decode_header(val):
            if isinstance(fragment, bytes):
                decoded_fragments.append(fragment.decode(encoding or "utf-8", errors="replace"))
            else:
                decoded_fragments.append(str(fragment))
        return " ".join(decoded_fragments).strip()
    except Exception:
        return str(val)


class EmailEngine:
    def __init__(
        self,
        db_path: str | Path | None = None,
        safety_gateway: Optional[SafetyGateway] = None,
    ) -> None:
        self._db_path = db_path
        self._safety = safety_gateway or SafetyGateway(db_path=db_path)
        init_assistant_database(self._db_path)

    @property
    def email_address(self) -> str:
        return os.environ.get("ZYE_EMAIL_ADDRESS", "").strip()

    @property
    def email_password(self) -> str:
        return os.environ.get("ZYE_EMAIL_APP_PASSWORD", "").strip()

    @property
    def imap_host(self) -> str:
        return os.environ.get("ZYE_IMAP_HOST", "imap.gmail.com").strip()

    @property
    def imap_port(self) -> int:
        try:
            return int(os.environ.get("ZYE_IMAP_PORT", "993"))
        except ValueError:
            return 993

    @property
    def smtp_host(self) -> str:
        return os.environ.get("ZYE_SMTP_HOST", "smtp.gmail.com").strip()

    @property
    def smtp_port(self) -> int:
        try:
            return int(os.environ.get("ZYE_SMTP_PORT", "465"))
        except ValueError:
            return 465

    def is_configured(self) -> bool:
        return bool(self.email_address and self.email_password)

    def classify_email_priority(self, subject: str, snippet: str) -> Tuple[str, str]:
        """
        Classify email urgency deterministically from subject and snippet.
        Returns (priority, reason).
        """
        combined = f"{subject} {snippet}".lower()
        for priority in ("CRITICAL", "HIGH", "LOW", "MEDIUM"):
            info = PRIORITY_KEYWORDS[priority]
            if any(kw in combined for kw in info["keywords"]):
                return priority, info["reason"]
        return "MEDIUM", "Normal work correspondence"

    def fetch_unread_emails(
        self,
        limit: int = 8,
        mark_read: bool = False,
        triage: bool = False,
    ) -> dict[str, Any]:
        """
        Fetch unread emails from IMAP SSL server using BODY.PEEK[] so messages
        are not marked as read prematurely.
        Extracts sender, subject, snippet, priority, and classification reason.
        """
        if not self.is_configured():
            return {
                "status": "CONFIG_REQUIRED",
                "message": "Email credentials not configured in environment (ZYE_EMAIL_ADDRESS, ZYE_EMAIL_APP_PASSWORD).",
                "unread_count": 0,
                "emails": [],
            }

        try:
            imap_to = float(os.environ.get("ZYE_IMAP_TIMEOUT", "6.0"))
            mail = imaplib.IMAP4_SSL(self.imap_host, port=self.imap_port, timeout=imap_to)
            mail.login(self.email_address, self.email_password)
            mail.select("INBOX")

            status, messages = mail.search(None, "UNSEEN")
            if status != "OK" or not messages[0]:
                try:
                    mail.logout()
                except Exception:
                    pass
                return {"status": "SUCCESS", "unread_count": 0, "emails": []}

            msg_ids = messages[0].split()
            selected_ids = msg_ids[-limit:]
            emails_list: list[dict[str, Any]] = []

            # Use BODY.PEEK[] to preserve UNSEEN state
            fetch_cmd = "(RFC822)" if mark_read else "(BODY.PEEK[])"

            for mid in reversed(selected_ids):
                status, data = mail.fetch(mid, fetch_cmd)
                if status != "OK" or not data:
                    continue

                raw_bytes = None
                for part in data:
                    if isinstance(part, tuple) and len(part) >= 2:
                        raw_bytes = part[1]
                        break

                if not raw_bytes:
                    continue

                msg = email.message_from_bytes(raw_bytes)
                subject = _decode_mime_words(msg.get("Subject", "No Subject"))
                sender = _decode_mime_words(msg.get("From", "Unknown"))
                date_str = msg.get("Date", "")

                # Extract plain-text snippet
                snippet = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                snippet = payload.decode("utf-8", errors="replace")[:300].strip()
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        snippet = payload.decode("utf-8", errors="replace")[:300].strip()

                priority, reason = self.classify_email_priority(subject, snippet)
                emails_list.append({
                    "id": mid.decode() if isinstance(mid, bytes) else str(mid),
                    "sender": sender,
                    "subject": subject,
                    "date": date_str,
                    "snippet": snippet,
                    "priority": priority,
                    "reason": reason,
                })

            if triage:
                emails_list.sort(key=lambda e: PRIORITY_RANK.get(e["priority"], 99))

            try:
                mail.logout()
            except Exception:
                pass

            _email_audit_logger.info("Fetched %d unread emails from %s", len(emails_list), self.email_address)
            return {
                "status": "SUCCESS",
                "unread_count": len(emails_list),
                "emails": emails_list,
            }

        except imaplib.IMAP4.error as a_err:
            logger.error("IMAP auth error: %s", a_err)
            _email_audit_logger.error("IMAP authentication failed for %s: %s", self.email_address, a_err)
            return {"status": "EMAIL_AUTH_FAILED", "message": f"IMAP authentication failed: {a_err}", "unread_count": 0, "emails": []}
        except Exception as e:
            logger.error("IMAP fetch failed: %s", e)
            _email_audit_logger.error("IMAP fetch error: %s", e)
            return {"status": "EMAIL_FETCH_FAILED", "message": f"IMAP connection or fetch failed: {e}", "unread_count": 0, "emails": []}

    def triage_unread(self, limit: int = 10) -> dict[str, Any]:
        """Fetch and return unread emails sorted deterministically by urgency with explanation reasons."""
        return self.fetch_unread_emails(limit=limit, triage=True)

    def create_draft(
        self,
        to_addr: str,
        subject: str,
        body: str,
        attachments: list[str] | None = None,
        tone: str = "Professional",
        priority: str = "MEDIUM",
    ) -> dict[str, Any]:
        """Store an email draft locally in SQLite without sending."""
        clean_to = to_addr.strip()
        if not clean_to:
            return {"status": "ERROR", "message": "Recipient address cannot be empty."}

        clean_sub = subject.strip()
        if not clean_sub:
            return {"status": "ERROR", "message": "Draft subject cannot be empty."}

        attachments_list = attachments or []
        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO email_drafts (to_addr, subject, body, attachments, tone, priority, created_at, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT');
                    """,
                    (clean_to, clean_sub, body.strip(), str(attachments_list), tone, priority, now_str),
                )
                draft_id = cursor.lastrowid

            _email_audit_logger.info("Draft created: id=%d, to=%s, subject='%s'", draft_id, clean_to, clean_sub)
            return {
                "status": "SUCCESS",
                "action": "DRAFT_CREATED",
                "draft_id": draft_id,
                "to_addr": clean_to,
                "subject": clean_sub,
                "tone": tone,
                "priority": priority,
                "body_preview": body[:120],
                "message": "Draft created successfully. Use action='send' with confirmed=True to send.",
            }
        finally:
            conn.close()

    def send_email(
        self,
        to_addr: str,
        subject: str,
        body: str,
        confirmed: bool = False,
        confirmation_id: str = "",
        attachments: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Send an email via SMTP SSL after Day 13 Negative Pre-Mortem Brain audit
        and mandatory explicit user confirmation.
        """
        clean_to = to_addr.strip()
        if not clean_to or not _EMAIL_REGEX.match(clean_to):
            return {"status": "EMAIL_INVALID_RECIPIENT", "message": f"Invalid recipient email address: '{to_addr}'"}

        if not subject.strip():
            return {"status": "ERROR", "message": "Email subject cannot be empty."}

        if not body.strip():
            return {"status": "ERROR", "message": "Email body cannot be empty."}

        attachments_list = attachments or []
        for att_path in attachments_list:
            p = Path(att_path)
            if not p.is_file():
                return {"status": "ERROR", "message": f"Attachment file not found: {att_path}"}
            if p.stat().st_size > 25 * 1024 * 1024:
                return {"status": "ERROR", "message": f"Attachment exceeds 25MB limit: {att_path}"}

        # Check SMTP configuration
        if not self.is_configured():
            _email_audit_logger.warning("SMTP dispatch unconfigured for %s", clean_to)
            return {
                "status": "CONFIG_REQUIRED",
                "message": "SMTP credentials not configured in environment (ZYE_EMAIL_ADDRESS, ZYE_EMAIL_APP_PASSWORD).",
            }

        # Day 13 Negative Pre-Mortem Brain Audit
        audit = self._safety.authorize_personal_assistant_action_sync(
            action_type="EMAIL_SEND",
            task_description=f"Send email to {clean_to}: '{subject}'",
            proposed_steps=[
                f"Verify recipient {clean_to}",
                f"Audit subject: {subject[:40]}",
                "Check SMTP connection availability",
                "Dispatch message via smtplib.SMTP_SSL",
            ],
            target_resources=[f"email:{clean_to}"],
        )

        if not audit.get("authorized", True):
            _email_audit_logger.error("Email send rejected by safety audit to %s: %s", clean_to, audit.get("reason"))
            return {
                "status": "BLOCKED_BY_SAFETY_AUDIT",
                "reason": audit.get("reason", "Safety audit rejected email dispatch"),
                "recipient": clean_to,
                "safety_audit": audit,
            }

        # Track valid issued confirmation tokens with operation binding and TTL
        if not hasattr(self, "_active_tokens") or not isinstance(self._active_tokens, dict):
            self._active_tokens = {}

        now_t = time.time()
        # Prune expired tokens older than 5 minutes
        self._active_tokens = {k: v for k, v in self._active_tokens.items() if v.get("expires_at", 0) > now_t}

        cid = confirmation_id.strip()
        is_confirmed = False
        if cid and cid in self._active_tokens:
            token_meta = self._active_tokens[cid]
            if (
                token_meta.get("recipient") == clean_to
                and token_meta.get("subject") == subject
                and now_t <= token_meta.get("expires_at", 0)
            ):
                self._active_tokens.pop(cid, None)
                is_confirmed = True
            else:
                _email_audit_logger.warning("Token mismatch or expired for email to %s: '%s'", clean_to, subject)

        if not is_confirmed:
            import uuid
            token = f"EMAIL_CONFIRM_{uuid.uuid4().hex[:12]}"
            self._active_tokens[token] = {
                "recipient": clean_to,
                "subject": subject,
                "created_at": now_t,
                "expires_at": now_t + 300.0,
            }
            _email_audit_logger.warning("Email send blocked pending confirmation to %s: '%s'", clean_to, subject)
            return {
                "status": "APPROVAL_REQUIRED",
                "message": f"Please confirm sending email to {clean_to} with subject '{subject}'. Pass confirmation_id='{token}' to execute.",
                "confirmation_id": token,
                "recipient": clean_to,
                "subject": subject,
                "body_preview": body[:120],
                "safety_audit": audit,
            }

        now_str = datetime.now(timezone.utc).isoformat()
        conn = get_db_connection(self._db_path)
        try:
            msg = email.message.EmailMessage()
            msg["From"] = self.email_address
            msg["To"] = clean_to
            msg["Subject"] = subject
            msg.set_content(body)

            with smtplib.SMTP_SSL(self.smtp_host, port=self.smtp_port, timeout=20) as smtp:
                smtp.login(self.email_address, self.email_password)
                smtp.send_message(msg)

            with conn:
                conn.execute(
                    """
                    INSERT INTO email_action_history (action_type, to_addr, subject, status, details, timestamp)
                    VALUES ('SEND', ?, ?, 'SENT', 'Dispatched successfully via SMTP SSL', ?);
                    """,
                    (clean_to, subject, now_str),
                )

            _email_audit_logger.info("SMTP_ACCEPTED for email to %s (subject='%s')", clean_to, subject)
            logger.info("Dispatched email successfully to %s", clean_to)
            return {
                "status": "SMTP_ACCEPTED",
                "recipient": clean_to,
                "subject": subject,
                "timestamp": now_str,
                "message": f"Email successfully accepted by SMTP server for delivery to {clean_to}.",
                "safety_audit": audit,
            }

        except smtplib.SMTPAuthenticationError as auth_err:
            logger.error("SMTP auth error: %s", auth_err)
            _email_audit_logger.error("SMTP Authentication failure: %s", auth_err)
            return {"status": "EMAIL_AUTH_FAILED", "message": f"SMTP Authentication failed: {auth_err}", "recipient": clean_to}
        except Exception as exc:
            logger.error("SMTP dispatch failed to %s: %s", clean_to, exc)
            _email_audit_logger.error("SMTP dispatch failed to %s: %s", clean_to, exc)
            with conn:
                conn.execute(
                    """
                    INSERT INTO email_action_history (action_type, to_addr, subject, status, details, timestamp)
                    VALUES ('SEND', ?, ?, 'FAILED', ?, ?);
                    """,
                    (clean_to, subject, str(exc), now_str),
                )
            return {
                "status": "SEND_FAILED",
                "message": f"SMTP dispatch failed: {exc}",
                "recipient": clean_to,
                "safety_audit": audit,
            }
        finally:
            conn.close()
