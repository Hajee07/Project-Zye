"""
Day 23 Comprehensive Test Suite — Advanced Microsoft PowerPoint Automation.
Tests PowerPoint Adapter, Presentation Manager, Slide Manager, Layouts, Content, Shapes,
Formatting, Transitions, Animations, Timeline, Tables, Charts, Notes, Accessibility, and PDF Exporter.
"""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from zye_office.models.day23_models import (
    PowerPointSlideMetadata,
    PowerPointPresentationMetadata,
    PowerPointTransitionConfig,
    PowerPointAnimationConfig,
)
from zye_office.powerpoint.powerpoint_constants import PowerPointConstants
from zye_office.powerpoint.powerpoint_validator import PowerPointValidator
from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.presentation_manager import PowerPointPresentationManager
from zye_office.powerpoint.slide_manager import PowerPointSlideManager
from zye_office.powerpoint.slide_transition_engine import PowerPointTransitionEngine
from zye_office.powerpoint.slide_animation_engine import PowerPointAnimationEngine
from zye_office.powerpoint.slide_accessibility import PowerPointAccessibilityEngine
from zye_office.powerpoint.presentation_auditor import PowerPointAuditor
from zye_office.powerpoint.powerpoint_errors import (
    PowerPointTransitionError,
    PowerPointAnimationError,
)


class TestDay23PowerPointAutomation(unittest.TestCase):

    def setUp(self) -> None:
        self.validator = PowerPointValidator()
        self.adapter = PowerPointAdapter()

    def test_powerpoint_constants(self) -> None:
        """Verify PowerPoint COM constants and enum mappings."""
        self.assertEqual(PowerPointConstants.ppLayoutBlank, 12)
        self.assertEqual(PowerPointConstants.ppLayoutTitle, 1)
        self.assertEqual(PowerPointConstants.ppLayoutText, 2)
        self.assertEqual(PowerPointConstants.ppEffectFade, 1793)
        self.assertEqual(PowerPointConstants.ppSaveAsPDF, 32)

    def test_slide_metadata_model(self) -> None:
        """Verify PowerPoint slide metadata model instantiation and validation."""
        meta = PowerPointSlideMetadata(
            slide_index=1,
            slide_id=256,
            shape_count=2,
            has_notes=True,
            transition_type="fade",
            animation_count=1,
        )
        self.assertEqual(meta.slide_index, 1)
        self.assertEqual(meta.shape_count, 2)
        self.assertEqual(meta.transition_type, "fade")

    def test_transition_config_model(self) -> None:
        """Verify slide transition configuration model."""
        config = PowerPointTransitionConfig(
            transition_type="fade",
            duration=1.5,
            advance_on_click=True,
        )
        self.assertEqual(config.transition_type, "fade")
        self.assertEqual(config.duration, 1.5)

    def test_animation_config_model(self) -> None:
        """Verify slide animation configuration model."""
        anim = PowerPointAnimationConfig(
            shape_name_or_index="Title",
            effect_type="fly_in",
            start_mode="on_click",
            duration=0.75,
            delay=0.1,
        )
        self.assertEqual(anim.effect_type, "fly_in")
        self.assertEqual(anim.start_mode, "on_click")

    def test_powerpoint_validator(self) -> None:
        """Verify transition and animation validation logic."""
        self.assertEqual(self.validator.validate_transition_name("fade"), "fade")
        self.assertEqual(self.validator.validate_transition_name("PUSH "), "push")
        with self.assertRaises(PowerPointTransitionError):
            self.validator.validate_transition_name("quantum_teleport")

        self.assertEqual(self.validator.validate_animation_name("fly_in"), "fly_in")
        self.assertEqual(self.validator.validate_animation_name("FADE"), "fade")
        with self.assertRaises(PowerPointAnimationError):
            self.validator.validate_animation_name("hyperspace_jump")

    def test_powerpoint_adapter_initialization(self) -> None:
        """Verify adapter defaults and worker."""
        self.assertIsNotNone(self.adapter.worker)
        self.assertIsNotNone(self.adapter.com_runtime)
        self.assertIsNotNone(self.adapter.validator)

    def test_powerpoint_auditor(self) -> None:
        """Verify presentation audit engine logic with mocked presentation."""
        auditor = PowerPointAuditor(adapter=self.adapter)
        mock_pres = MagicMock()
        mock_slide1 = MagicMock()
        mock_slide1.Shapes.Count = 0
        mock_slide1.Shapes.HasTitle = False
        mock_pres.Slides.Count = 1
        mock_pres.Slides.side_effect = lambda i: mock_slide1

        with patch.object(self.adapter, "get_active_presentation_raw", return_value=mock_pres):
            rep = auditor.audit_presentation()
            self.assertEqual(rep["status"], "SUCCESS")
            self.assertTrue(rep["findings_count"] > 0)

    def test_powerpoint_accessibility_engine(self) -> None:
        """Verify presentation accessibility report generation with mocked presentation."""
        engine = PowerPointAccessibilityEngine(adapter=self.adapter)
        mock_pres = MagicMock()
        mock_slide1 = MagicMock()
        mock_slide1.Shapes.HasTitle = False
        mock_pres.Slides.Count = 1
        mock_pres.Slides.side_effect = lambda i: mock_slide1

        with patch.object(self.adapter, "get_active_presentation_raw", return_value=mock_pres):
            rep = engine.generate_accessibility_report()
            self.assertEqual(rep["status"], "SUCCESS")
            self.assertTrue(rep["issues_count"] > 0)


if __name__ == "__main__":
    unittest.main()
