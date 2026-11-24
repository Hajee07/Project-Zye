# Zye AI — Day 23 Slide Animation Engine

## 1. Overview

The `PowerPointAnimationEngine` manipulates the `MainSequence` timeline of PowerPoint slides to introduce, emphasize, or transition shapes and text frames dynamically via voice or MCP tools.

---

## 2. Supported Animation Effects

Animations map directly to the Microsoft PowerPoint `MsoAnimEffect` enumeration:

| Effect Name | Effect Enum | Category | Description |
|---|---|---|---|
| `fly_in` | `msoAnimEffectFly` (2) | Entrance | Smooth flight into the slide viewport |
| `fade` | `msoAnimEffectFade` (10) | Entrance | Gradual opacity transition |
| `appear` | `msoAnimEffectAppear` (1) | Entrance | Instantaneous visibility |
| `zoom` | `msoAnimEffectZoom` (23) | Entrance | Expanding scaling from focal point |
| `split` | `msoAnimEffectSplit` (9) | Entrance | Center or edge revealing transition |
| `wipe` | `msoAnimEffectWipe` (22) | Entrance | Directional sweep across the shape |

---

## 3. Trigger & Timing Modes

Effects can be sequenced using `MsoAnimTriggerType`:
- `on_click` (`msoAnimTriggerOnPageClick` = 1): Waits for presentation advance or mouse click.
- `with_previous` (`msoAnimTriggerWithPrevious` = 2): Starts concurrently with preceding animation.
- `after_previous` (`msoAnimTriggerAfterPrevious` = 3): Executes sequentially immediately following previous animation duration.

---

## 4. Safety & Validation

- `PowerPointValidator.validate_animation_name`: Whitelists trusted animations; rejects unknown or corrupted effect strings with `PowerPointAnimationError`.
- `PowerPointAnimationEngine.clear_timeline`: Safely empties slide timeline without deleting underlying shapes.
