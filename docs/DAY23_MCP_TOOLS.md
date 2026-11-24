# Zye AI — Day 23 FastMCP Tools Catalog

The unified `office_master_mcp.py` exposes **183 live COM automation tools**, including 64 tools introduced in Day 23:

## 1. PowerPoint Automation Suite (37 Tools)

1. `powerpoint_inspect_live`: Inspect active PowerPoint instance, slide count, and presentation state.
2. `powerpoint_create_presentation`: Create a new blank presentation.
3. `powerpoint_open_presentation`: Open existing `.pptx` presentation.
4. `powerpoint_save_presentation`: Save active presentation.
5. `powerpoint_save_as`: Save active presentation to specified path.
6. `powerpoint_close_presentation`: Close presentation cleanly.
7. `powerpoint_get_slides`: Enumerate all slides in active presentation.
8. `powerpoint_add_slide`: Insert slide with specified layout index.
9. `powerpoint_duplicate_slide`: Duplicate slide by index.
10. `powerpoint_delete_slide`: Delete slide (destructive, requires `confirmed=True`).
11. `powerpoint_move_slide`: Reorder slide from one position to another.
12. `powerpoint_hide_slide`: Toggle slide visibility during presentations.
13. `powerpoint_change_layout`: Apply slide layout preset.
14. `powerpoint_set_title`: Set slide title text.
15. `powerpoint_add_text`: Append text to body placeholder.
16. `powerpoint_add_bullets`: Add structured bullet list.
17. `powerpoint_add_shape`: Insert AutoShape (rectangle, oval, etc.).
18. `powerpoint_add_textbox`: Insert standalone textbox.
19. `powerpoint_delete_shape`: Remove shape by name or index.
20. `powerpoint_format_text`: Format font, size, style, and color.
21. `powerpoint_set_background`: Apply solid background color.
22. `powerpoint_apply_theme`: Load and apply Office `.thmx` theme.
23. `powerpoint_set_transition`: Apply transition to a single slide.
24. `powerpoint_set_all_transitions`: Apply uniform transition to all slides.
25. `powerpoint_get_transitions`: Query transitions across all slides.
26. `powerpoint_add_animation`: Add animation effect to slide shape.
27. `powerpoint_remove_animation`: Remove animation by timeline index.
28. `powerpoint_get_animations`: Enumerate MainSequence timeline effects.
29. `powerpoint_clear_timeline`: Remove all animations on a slide.
30. `powerpoint_add_table`: Insert table and populate with 2D data.
31. `powerpoint_add_chart`: Insert native Office chart (column, bar, line, pie).
32. `powerpoint_insert_picture`: Insert image file with positioning.
33. `powerpoint_add_notes`: Add speaker notes to slide.
34. `powerpoint_get_notes`: Retrieve speaker notes from slide.
35. `powerpoint_audit_presentation`: Scan for empty placeholders, missing titles.
36. `powerpoint_accessibility_report`: Audit alt-text and accessibility standards.
37. `powerpoint_export_pdf`: Export presentation to native high-fidelity PDF.

---

## 2. Outlook Automation Suite (23 Tools)

38. `outlook_inspect_live`: Inspect active Outlook instance and default folders.
39. `outlook_get_unread_count`: Get unread count from default Inbox.
40. `outlook_get_recent_messages`: List recent Inbox emails.
41. `outlook_search_messages`: Search emails by sender, subject, or unread status.
42. `outlook_read_message`: Read message body, recipients, and attachments.
43. `outlook_create_draft`: Create and save email draft (Draft-First Policy).
44. `outlook_reply_to_message`: Create draft reply.
45. `outlook_forward_message`: Create draft forward.
46. `outlook_add_attachment`: Attach file to existing draft.
47. `outlook_prepare_send`: Pre-send inspection and confirmation preview.
48. `outlook_send_authorized`: Transmit authorized email (`confirmed=True` mandatory).
49. `outlook_get_folders`: Enumerate folders in default MAPI store.
50. `outlook_create_folder`: Create new Inbox subfolder.
51. `outlook_move_message`: Move email to destination folder.
52. `outlook_get_categories`: List configured color categories.
53. `outlook_assign_category`: Tag message with color category.
54. `outlook_mark_read`: Mark email as read or unread.
55. `outlook_search_contacts`: Search Contacts folder by name or email.
56. `outlook_create_contact`: Add new contact to Contacts folder.
57. `outlook_get_tasks`: Retrieve tasks from Tasks folder.
58. `outlook_create_task`: Create new task item.
59. `outlook_get_calendar_items`: List upcoming calendar appointments.
60. `outlook_create_calendar_item`: Schedule calendar appointment.

---

## 3. Desktop UI Automation Suite (4 Tools)

61. `desktop_inspect_active_window`: Inspect focused window title, process name, and HWND.
62. `desktop_inspect_app_ui`: Query accessible UI controls via UIA.
63. `desktop_execute_keyboard_sequence`: Bounded keystroke execution with focus verification.
64. `desktop_trigger_ribbon_accelerator`: Office Ribbon tab Alt-key shortcut trigger.
