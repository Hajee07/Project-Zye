@echo off
title ZYE AI - Live Voice Assistant v4.0
cd /d "D:\Zye"
echo ================================================================
echo           ZYE AI - LIVE VOICE ASSISTANT v4.0
echo ================================================================
echo Starting Zye Voice Engine (Gemini Live Native Audio)...
"D:\Zye\.venv\Scripts\python.exe" -u main.py --voice
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Zye exited with error code %ERRORLEVEL%.
)
pause
