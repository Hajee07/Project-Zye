"""
Data Models & Pydantic Schemas for PowerPoint, Outlook, and Universal Desktop UI — Zye Day 23.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field


# =============================================================================
# PowerPoint Models
# =============================================================================

class PPTXTransitionType(str, Enum):
    NONE = "none"
    FADE = "fade"
    PUSH = "push"
    WIPE = "wipe"
    SPLIT = "split"
    CUT = "cut"
    REVEAL = "reveal"
    RANDOM = "random"
    COVER = "cover"
    UNCOVER = "uncover"


class PPTXAnimationType(str, Enum):
    # Entrance
    APPEAR = "appear"
    FADE = "fade"
    FLY_IN = "fly_in"
    FLOAT_IN = "float_in"
    SPLIT = "split"
    WIPE = "wipe"
    ZOOM = "zoom"
    # Emphasis
    PULSE = "pulse"
    SPIN = "spin"
    GROW_SHRINK = "grow_shrink"
    TEETER = "teeter"
    # Exit
    DISAPPEAR = "disappear"
    FLY_OUT = "fly_out"
    FLOAT_OUT = "float_out"


class PowerPointPresentationMetadata(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "powerpoint"
    presentation_name: str = ""
    filename: Optional[str] = None
    path: Optional[str] = None
    slide_count: int = 0
    active_slide_index: int = 1
    active_slide_title: Optional[str] = None
    slide_titles: List[str] = Field(default_factory=list)
    is_saved: bool = True
    is_read_only: bool = False
    slide_width: float = 960.0
    slide_height: float = 540.0
    has_notes: bool = False
    message: Optional[str] = None


class PowerPointSlideMetadata(BaseModel):
    status: str = "SUCCESS"
    slide_index: int = 1
    slide_id: Optional[int] = None
    title: Optional[str] = None
    shape_count: int = 0
    has_notes: bool = False
    notes_text: Optional[str] = None
    layout_name: Optional[str] = None
    transition_type: Optional[str] = None
    transition_duration: Optional[float] = None
    animation_count: int = 0
    is_hidden: bool = False


class PowerPointShapeMetadata(BaseModel):
    shape_name: str = ""
    shape_id: int = 0
    shape_type: str = "rectangle"
    text: Optional[str] = None
    left: float = 0.0
    top: float = 0.0
    width: float = 0.0
    height: float = 0.0
    has_text_frame: bool = False


class PowerPointTransitionConfig(BaseModel):
    slide_range: str = "all"  # "all", "active", "1,2,3", "1-5"
    transition_type: str = "fade"
    duration: float = 1.0
    advance_on_click: bool = True
    advance_after_time: Optional[float] = None


class PowerPointAnimationConfig(BaseModel):
    slide_index: int = 1
    shape_name_or_index: Union[str, int] = "Title"
    effect_type: str = "fly_in"
    effect_category: str = "entrance"  # entrance, emphasis, exit
    duration: float = 0.75
    delay: float = 0.0
    start_mode: str = "on_click"  # on_click, with_previous, after_previous


# =============================================================================
# Outlook Models
# =============================================================================

class OutlookMailboxSummary(BaseModel):
    status: str = "SUCCESS"
    app_name: str = "outlook"
    profile_name: Optional[str] = None
    account_name: Optional[str] = None
    default_store_name: Optional[str] = None
    inbox_unread_count: int = 0
    inbox_total_count: int = 0
    sent_count: int = 0
    drafts_count: int = 0


class OutlookMessageMetadata(BaseModel):
    status: str = "SUCCESS"
    entry_id: Optional[str] = None
    subject: str = ""
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    received_time: Optional[str] = None
    is_unread: bool = False
    has_attachments: bool = False
    attachment_names: List[str] = Field(default_factory=list)
    body_preview: Optional[str] = None
    importance: int = 1  # 0=low, 1=normal, 2=high
    categories: Optional[str] = None


class OutlookDraftConfig(BaseModel):
    to_recipients: List[str] = Field(default_factory=list)
    cc_recipients: List[str] = Field(default_factory=list)
    bcc_recipients: List[str] = Field(default_factory=list)
    subject: str = ""
    body: str = ""
    html_body: Optional[str] = None
    importance: int = 1
    attachment_paths: List[str] = Field(default_factory=list)
    categories: Optional[str] = None


class OutlookAttachmentMetadata(BaseModel):
    filename: str = ""
    file_size_bytes: int = 0
    extension: str = ""
    is_executable: bool = False


# =============================================================================
# Universal Desktop UI Models
# =============================================================================

class DesktopWindowMetadata(BaseModel):
    status: str = "SUCCESS"
    handle: int = 0
    title: str = ""
    process_name: str = ""
    process_id: int = 0
    class_name: Optional[str] = None
    is_foreground: bool = True
    bounding_rectangle: Optional[Dict[str, int]] = None


class DesktopUIControlMetadata(BaseModel):
    control_name: str = ""
    control_type: str = "Button"
    automation_id: Optional[str] = None
    class_name: Optional[str] = None
    is_enabled: bool = True
    is_visible: bool = True
    has_keyboard_focus: bool = False


class DesktopKeyboardSequenceConfig(BaseModel):
    target_process: Optional[str] = None
    keys: List[str] = Field(default_factory=list)
    interval_seconds: float = 0.05
    require_foreground_focus: bool = True
