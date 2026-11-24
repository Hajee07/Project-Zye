# Zye AI — Day 23 PowerPoint COM Architecture & Engineering Specification

## 1. Executive Summary

Day 23 establishes the enterprise-grade Microsoft PowerPoint COM automation foundation for the Zye AI Hybrid Assistant. Built upon the dedicated Single-Threaded Apartment (STA) COM Worker (`STACOMWorker`), the system provides robust, non-blocking control over `PowerPoint.Application` (build 16.0) with zero arbitrary script execution risk.

---

## 2. Architectural Blueprint

```
┌─────────────────────────────────────────────────────────────┐
│                 Zye Main / FastMCP Client                   │
└──────────────────────────────┬──────────────────────────────┘
                               │
                Day23MCPIntegrationFacade
                               │
         ┌─────────────────────┼─────────────────────┐
         ▼                     ▼                     ▼
  PowerPointAdapter     OutlookAdapter     DesktopUIInspector
         │
  STACOMWorker (Apartment Threaded CoInitializeEx)
         │
  PowerPoint Object Model (PowerPoint.Application 16.0)
   ├── Presentations (Create, Open, Save, Close)
   ├── Slides (Add, Duplicate, Move, Delete, Layout)
   ├── Shapes & Content (Text, Bullets, AutoShapes, Tables, Charts, Pictures)
   ├── Transitions (SlideShowTransition, Duration, AdvanceOnClick)
   ├── Animations (MainSequence Effects, Fly-In, Fade, Timing)
   ├── Notes (Speaker Notes per Slide)
   ├── Accessibility (Auditor, Missing Alt-Text, Empty Titles)
   └── Exporter (Native FixedFormat PDF Export)
```

---

## 3. Subsystem Breakdown

1. **PowerPointAdapter (`zye_office/powerpoint/powerpoint_adapter.py`)**:
   - Manages connection lifecycle via `OfficeCOMRuntime` using `ConnectionPolicy.AUTO_ATTACH_OR_LAUNCH` or `ATTACH_EXISTING`.
   - Thread-affine execution guarantees all COM calls run exclusively on the dedicated STA worker thread.

2. **PresentationManager (`zye_office/powerpoint/presentation_manager.py`)**:
   - Manages presentations: creation, opening, saving with overwrite protection, and clean teardown.

3. **SlideManager (`zye_office/powerpoint/slide_manager.py`)**:
   - 1-based indexing conforming to the PowerPoint Object Model.
   - Operations: `add_slide`, `duplicate_slide`, `delete_slide` (confirmation gated), `move_slide`, `hide_slide`.

4. **Content & Shape Engines**:
   - `PowerPointContentEngine`: Sets titles, appends body text, and inserts structured bullet points.
   - `PowerPointShapeEngine`: Inserts standard AutoShapes (rectangles, ovals) and standalone textboxes.
   - `PowerPointTableEngine`: Creates grid tables and populates 2D data matrices.
   - `PowerPointChartEngine`: Embeds native Office charts (column, bar, line, pie).
   - `PowerPointMediaEngine`: Inserts images with geometry placement and dimension scaling.

5. **SlideNotesEngine (`zye_office/powerpoint/slide_notes_engine.py`)**:
   - Manipulates `Slide.NotesPage` text ranges for executive speaker notes and presentation commentary.

6. **Exporter (`zye_office/powerpoint/presentation_exporter.py`)**:
   - Uses native `Presentation.ExportAsFixedFormat` with `ppFixedFormatTypePDF = 2`.
   - Strictly validates destination path, prevents path traversal, and verifies output file byte size > 0.
