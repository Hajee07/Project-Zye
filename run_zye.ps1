$Host.UI.RawUI.WindowTitle = "ZYE AI - Live Voice Assistant v4.0"
Set-Location -Path "D:\Zye"
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "          ZYE AI - LIVE VOICE ASSISTANT v4.0" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Starting Zye Voice Engine (Gemini Live Native Audio)..." -ForegroundColor Green
& "D:\Zye\.venv\Scripts\python.exe" -u main.py --voice
Read-Host "Press Enter to exit..."
