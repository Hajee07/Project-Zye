# ZYE AI — Windows Installed Application Discovery Engine

## 1. Overview & Mechanics

The Windows Installed Application Discovery engine (`zye_windows/app_discovery.py` & `zye_windows/app_catalog.py`) provides discovery and resolution of all installed software on the user's laptop without requiring manual paths.

```
                      +-----------------------------+
                      | User Voice / Intent Query   |
                      |   "Open Chrome", "Word"     |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      | WindowsAppCatalog           |
                      | - Name Normalization        |
                      | - Memory Cache (TTL: 3600s) |
                      | - Disk Cache: app_cache.json|
                      +-----------------------------+
                                     | (Cache miss or force refresh)
                                     v
                      +-----------------------------+
                      | WindowsAppDiscovery         |
                      | - PowerShell Get-StartApps  |
                      | - AppUserModelID (AUMID)    |
                      | - Registry Fallbacks        |
                      +-----------------------------+
                                     |
                                     v
                      +-----------------------------+
                      | Discovered Application Info |
                      | - Name, AppID, Type         |
                      | - (Win32, Store, System)    |
                      +-----------------------------+
```

---

## 2. Discovery Methods

1. **PowerShell `Get-StartApps`**:
   Extracts `Name` and `AppID` for all registered applications in the Start Menu and Windows Store.
2. **AUMID Pattern Classification**:
   - `STORE / UWP`: Contains package identity markers (e.g., `!App`, `_cv1g1gvanyjgm`, `_8wekyb3d8bbwe`).
   - `WIN32`: Contains file paths or standard `.exe` executables.
   - `SYSTEM`: Windows shell utilities (`explorer.exe`, immersive control panel).
3. **Local Cache**:
   Applications are cached in `data/windows_app_cache.json` with a 3600-second TTL to ensure instantaneous lookup (< 5ms) on conversational requests.

---

## 3. Target Application Mappings

| Common Voice Name | Discovered Name | AppID / AUMID | Installation Type |
|---|---|---|---|
| **Google Chrome** | Google Chrome | `Chrome` | WIN32 |
| **WhatsApp** | WhatsApp | `5319275A.WhatsAppDesktop_cv1g1gvanyjgm!App` | STORE (UWP) |
| **Microsoft Word** | Word | `Microsoft.Office.WINWORD.EXE.15` | WIN32 |
| **Microsoft Excel** | Excel | `Microsoft.Office.EXCEL.EXE.15` | WIN32 |
| **Microsoft PowerPoint** | PowerPoint | `Microsoft.Office.POWERPNT.EXE.15` | WIN32 |
| **Microsoft Outlook** | Outlook | `Microsoft.Office.OUTLOOK.EXE.15` | WIN32 |
| **Notepad** | Notepad | `Microsoft.WindowsNotepad_8wekyb3d8bbwe!App` | STORE (UWP) |
| **Calculator** | Calculator | `Microsoft.WindowsCalculator_8wekyb3d8bbwe!App` | STORE (UWP) |
| **Visual Studio Code** | Visual Studio Code | `Microsoft.VisualStudioCode` | WIN32 |
