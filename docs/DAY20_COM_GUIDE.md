# Zye AI — Day 20 Windows COM Automation Guide

## 1. Windows COM Architecture & Apartment Threading

Component Object Model (COM) on Microsoft Windows requires strict apartment-threading discipline. In a multithreaded Python application (such as an asyncio FastMCP server or worker pools), accessing COM interfaces across thread boundaries without marshaling leads directly to:
```
pywintypes.com_error: (-2147417842, 'The application called an interface that was marshalled for a different thread.', None, None)
HRESULT: 0x8001010E (RPC_E_WRONG_THREAD)
```

To eliminate this class of error, Zye implements the **Single-Threaded Apartment (STA) COM Worker** pattern.

---

## 2. STA Worker Pattern Implementation

All interactions with `win32com.client` and live Office applications execute exclusively inside `STACOMWorker`:

```python
import pythoncom
import threading
import queue

class STACOMWorker:
    def _worker_loop(self):
        # Explicit initialization of the single-threaded apartment
        pythoncom.CoInitializeEx(pythoncom.COINIT_APARTMENTTHREADED)
        try:
            while not self._stop_event.is_set():
                task = self._queue.get()
                if task is None:
                    break
                func, args, kwargs, future = task
                try:
                    res = func(*args, **kwargs)
                    future.set_result(res)
                except Exception as e:
                    future.set_exception(e)
        finally:
            pythoncom.CoUninitialize()
```

### Key Rules:
1. **Never pass raw COM pointers out of the worker:**
   Functions running on the STA worker must return Python primitives, dictionaries, or Pydantic models. Raw `CDispatch` pointers must stay inside `OfficeCOMRuntime._sta_com_objects`.
2. **Re-entrant safe execution:**
   If a function executing on the worker calls another helper that requests worker execution, `worker.run()` detects `threading.get_ident() == self._thread_id` and executes directly without queuing or deadlocking.

---

## 3. Supported Office Applications & ProgIDs

| Application | ProgID | Process Executable | Window Class | Default Connection |
|-------------|--------|---------------------|--------------|-------------------|
| Microsoft Word | `Word.Application` | `WINWORD.EXE` | `OpusApp` | `ATTACH_EXISTING` |
| Microsoft Excel | `Excel.Application` | `EXCEL.EXE` | `XLMAIN` | `ATTACH_EXISTING` |
| Microsoft PowerPoint | `PowerPoint.Application` | `POWERPNT.EXE` | `PPTFrameClass` | `ATTACH_EXISTING` |
| Microsoft Outlook | `Outlook.Application` | `OUTLOOK.EXE` | `rctrl_renwnd32` | `ATTACH_EXISTING` |

---

## 4. Connection Policies

Zye supports 4 connection policies via `ConnectionPolicy`:
1. `ATTACH_EXISTING`: Attaches to an already-open Office instance via `win32com.client.GetActiveObject(prog_id)`. If no instance is running, returns `OFFICE_APP_NOT_RUNNING`.
2. `LAUNCH_NEW`: Creates a new instance using `win32com.client.Dispatch(prog_id)` and sets `app.Visible = True`.
3. `AUTO_ATTACH_OR_LAUNCH`: Tries `GetActiveObject` first; if unavailable, falls back to `Dispatch`.
4. `INSPECT_ONLY`: Queries the running object table without modifying application state.

---

## 5. Native COM Document Manipulation

### 5.1 Microsoft Word
- `ActiveDocument.Content.InsertAfter(text)`
- `Selection.TypeText(text)`
- `ActiveDocument.TrackRevisions = True / False`
- `ActiveDocument.ComputeStatistics(wdStatisticWords)`
- `ActiveDocument.ExportAsFixedFormat(output_path, ExportFormat=17)`

### 5.2 Microsoft Excel
- `ActiveSheet.Range("A1").Value = 100`
- `ActiveSheet.Range("B10").Formula = "=SUM(B1:B9)"`
- `Range.Font.Bold = True`, `Range.Font.Size = 14`
- `Application.Calculate()`
- `ActiveWorkbook.ExportAsFixedFormat(Type=0, Filename=output_path)`

### 5.3 Microsoft PowerPoint
- `ActivePresentation.Slides(index).Shapes.Count`
- `ActivePresentation.Slides.Add(index, layout)`
- `Slide.Shapes.Title.TextFrame.TextRange.Text = "New Title"`
- `ActivePresentation.ExportAsFixedFormat(output_path, FixedFormatType=2)`

### 5.4 Microsoft Outlook
- `app.CreateItem(0)` (olMailItem = 0)
- `mail.Subject = subject`, `mail.Body = body`, `mail.To = recipient`
- `mail.Save()` (Strictly saved to Drafts folder; never automatically sent)
- `ns.GetDefaultFolder(6).UnReadItemCount` (olFolderInbox = 6)
