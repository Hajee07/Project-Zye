# Zye AI — Day 23 Slide Master & Theme Engine

## 1. Overview

The `PowerPointSlideMasterEngine` and `PowerPointThemeEngine` govern document-wide branding, typographical hierarchies, color palettes, and presentation templates.

---

## 2. Capabilities

1. **Slide Master Inspection**:
   - Inspects `Presentation.SlideMaster` shapes, background properties, and custom layout masters.
2. **Theme Application**:
   - Applies `.thmx` Office theme files via `Presentation.ApplyTheme()`.
   - Validates theme path with `OfficePathValidator` to prevent path traversal or loading malicious binaries.
3. **Slide Background Control**:
   - `set_slide_background(slide_index, color_bgr)`: Applies a solid BGR color directly to `Slide.Background.Fill.Solid()`.
