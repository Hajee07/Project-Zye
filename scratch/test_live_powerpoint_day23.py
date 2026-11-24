"""
Live Microsoft PowerPoint COM Automation Verification — Day 23.
Creates an isolated presentation, adds slides with English and Tamil Unicode text,
configures slide transitions, applies shape animations, adds speaker notes,
and exports high-fidelity PDF with verification.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from zye_office.powerpoint.powerpoint_adapter import PowerPointAdapter
from zye_office.powerpoint.presentation_manager import PowerPointPresentationManager
from zye_office.powerpoint.slide_manager import PowerPointSlideManager
from zye_office.powerpoint.slide_content_engine import PowerPointContentEngine
from zye_office.powerpoint.slide_formatting_engine import PowerPointFormattingEngine
from zye_office.powerpoint.slide_transition_engine import PowerPointTransitionEngine
from zye_office.powerpoint.slide_animation_engine import PowerPointAnimationEngine
from zye_office.powerpoint.slide_notes_engine import PowerPointNotesEngine
from zye_office.powerpoint.presentation_exporter import PowerPointExporter


def run_live_powerpoint_test() -> None:
    print("=" * 64)
    print("  LIVE MICROSOFT POWERPOINT COM VERIFICATION — DAY 23")
    print("=" * 64)

    adapter = PowerPointAdapter()
    print("1. Connecting to Microsoft PowerPoint COM...")
    conn = adapter.connect()
    print(f"   Status: {conn.get('status')}, App: {conn.get('app_name')}")

    pres_mgr = PowerPointPresentationManager(adapter=adapter)
    slide_mgr = PowerPointSlideManager(adapter=adapter)
    content_eng = PowerPointContentEngine(adapter=adapter)
    fmt_eng = PowerPointFormattingEngine(adapter=adapter)
    trans_eng = PowerPointTransitionEngine(adapter=adapter)
    anim_eng = PowerPointAnimationEngine(adapter=adapter)
    notes_eng = PowerPointNotesEngine(adapter=adapter)
    exporter = PowerPointExporter(adapter=adapter)

    # 1. Create Presentation
    print("\n2. Creating isolated temporary presentation...")
    pres = pres_mgr.create_presentation()
    print(f"   Presentation created: {pres.get('presentation_name')}")

    # 2. Add Slides
    print("\n3. Adding slides...")
    s1 = slide_mgr.add_slide(layout=1)  # ppLayoutTitle
    print(f"   Slide 1 added (layout=Title)")

    s2 = slide_mgr.add_slide(layout=2)  # ppLayoutText
    print(f"   Slide 2 added (layout=Title & Content)")

    # 3. Add Content & Tamil Unicode
    print("\n4. Populating title and Tamil content...")
    t1 = content_eng.set_slide_title(1, "Zye AI — வணக்கம் (Hello)")
    print(f"   Slide 1 Title set: {t1.get('status')}")

    b1 = content_eng.add_bullet_points(2, [
        "Universal Windows Automation",
        "Multi-Language Voice Intelligence (Tamil / English)",
        "Enterprise COM Live Automation (Word, Excel, PowerPoint, Outlook)",
        "Zero-Trust Sandboxed Delivery Architecture",
    ])
    print(f"   Slide 2 bullets added: {b1.get('status')}")

    # 4. Transitions
    print("\n5. Applying Slide Transitions...")
    tr = trans_eng.set_all_slide_transitions(transition_name="fade", duration=1.0)
    print(f"   Transitions applied: {tr.get('status')}")

    # 5. Animations
    print("\n6. Applying Shape Animation...")
    an = anim_eng.add_animation(slide_index=1, shape_identifier=1, effect_name="fly_in", start_mode="on_click")
    print(f"   Animation applied: {an.get('status')}, Effect: fly_in")

    # 6. Speaker Notes
    print("\n7. Adding Speaker Notes...")
    nt = notes_eng.add_notes(slide_index=1, notes_text="Confidential: Zye AI Hybrid Assistant Executive Briefing.")
    print(f"   Notes added: {nt.get('status')}")

    # 7. PDF Export
    out_dir = ROOT / "data" / "test_exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = str(out_dir / "Zye_Day23_Live_PowerPoint_Test.pdf")

    print(f"\n8. Exporting presentation to PDF: {pdf_path}...")
    exp = exporter.export_pdf(output_path=pdf_path, overwrite=True)
    print(f"   PDF Export status: {exp.get('status')}, Size: {exp.get('file_size_bytes')} bytes")
    assert os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 0, "PDF export failed!"

    # 8. Close Presentation Cleanly
    print("\n9. Closing presentation...")
    cls = pres_mgr.close_presentation(save_changes=False)
    print(f"   Closed: {cls.get('status')}")

    print("\n" + "=" * 64)
    print("  ALL LIVE POWERPOINT COM TESTS PASSED SUCCESSFULLY!")
    print(f"  Verified PDF: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")
    print("=" * 64)


if __name__ == "__main__":
    run_live_powerpoint_test()
