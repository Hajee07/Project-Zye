# Zye AI — Day 23 Slide Transition Engine

## 1. Overview

The `PowerPointTransitionEngine` controls `SlideShowTransition` properties on individual slides or across the entire presentation, providing professional presentation delivery.

---

## 2. Transition Mapping & Verified COM Enums

In Microsoft PowerPoint 16.0, `SlideShowTransition.EntryEffect` accepts specific `PpEntryEffect` values:

| Transition Name | EntryEffect Enum | Integer Value | Description |
|---|---|---|---|
| `none` | `ppEffectNone` | `0` | Instantaneous slide cut |
| `cut` | `ppEffectCut` | `257` | Direct cut transition |
| `fade` | `ppEffectFade` | `1793` | Classic cross-fade transition |
| `fade_smoothly` | `ppEffectFadeSmoothly` | `3849` | High-smoothness opacity fade |
| `push` | `ppEffectPushLeft` | `3844` | Horizontal slide push |
| `wipe` | `ppEffectWipeRight` | `2819` | Linear horizontal wipe |
| `cover` | `ppEffectCoverLeft` | `1282` | Incoming slide overlay cover |
| `uncover` | `ppEffectUncoverRight` | `1539` | Outgoing slide uncover sweep |

---

## 3. Global vs. Per-Slide Application

- `set_slide_transition(slide_index, transition_name, duration)`: Targets a specific slide.
- `set_all_slide_transitions(transition_name, duration)`: Iterates across all presentation slides and sets uniform transitions in a single atomic STA transaction.
