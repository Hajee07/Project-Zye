# ZYE AI — Installed Application Automation Capability Matrix

**Discovery Inventory:** 186 Registered Applications Discovered on Host Machine  
**Discovery Protocol:** PowerShell `Get-StartApps` + Windows Registry + AppUserModelID (AUMID)  
**Host Platform:** Windows 11 Desktop (x64)  

---

## 1. Core Target Applications Capability Matrix

| Application | Discovery Name | AppID / AUMID | Type | Launch Command | Window Emergence | Focus & UI Inspection | Automated Action Capabilities |
|---|---|---|---|---|---|---|---|
| **Google Chrome** | Google Chrome | `Chrome` | WIN32 | `chrome.exe` / `shell:AppsFolder\Chrome` | Verified (HWND) | Verified (UIA + Playwright) | Launch, navigate, search, summarize page, Gmail search, Drive search |
| **WhatsApp Desktop** | WhatsApp | `5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App` | STORE | `shell:AppsFolder\5319275A.WhatsAppDesktop...` | Verified (HWND) | Verified (UIA Tree) | Search contact, open chat, compose draft (safe), send message (confirmed), call control |
| **Microsoft Word** | Word | `Microsoft.Office.WINWORD.EXE.15` | WIN32 | `winword.exe` | Verified (HWND) | Verified (COM Dispatch) | Create doc, insert text, format, tables, save, export PDF |
| **Microsoft Excel** | Excel | `Microsoft.Office.EXCEL.EXE.15` | WIN32 | `excel.exe` | Verified (HWND) | Verified (COM Dispatch) | Create workbook, cell values, formulas, charts, recalculation, save, export PDF |
| **Microsoft PowerPoint** | PowerPoint | `Microsoft.Office.POWERPNT.EXE.15` | WIN32 | `powerpnt.exe` | Verified (HWND) | Verified (COM Dispatch) | Create presentation, add slides, shapes, text, save, export PDF |
| **Microsoft Outlook** | Outlook | `Microsoft.Office.OUTLOOK.EXE.15` | WIN32 | `outlook.exe` | Verified (HWND) | Verified (COM Dispatch) | Inspect version, create email draft, list unread emails |
| **Windows Notepad** | Notepad | `Microsoft.WindowsNotepad_8wekyb3d8bbwe!App` | STORE | `notepad.exe` | Verified (HWND: 196876) | Verified (UIA Tree) | Launch in 0.52s, type text, window management, close |
| **Windows Calculator** | Calculator | `Microsoft.WindowsCalculator_8wekyb3d8bbwe!App` | STORE | `calc.exe` | Verified (HWND) | Verified (UIA Tree) | Launch, button clicks, result extraction |
| **Visual Studio Code** | Visual Studio Code | `Microsoft.VisualStudioCode` | WIN32 | `code.cmd` | Verified (HWND) | Verified (Window Mgr) | Launch, focus workspace, file inspection |
