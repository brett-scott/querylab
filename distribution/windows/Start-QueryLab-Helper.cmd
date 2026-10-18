@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -STA -ExecutionPolicy Bypass -File "%~dp0scripts\launch-helper.ps1"
if errorlevel 1 (
  echo QueryLab Helper could not open. Extract the entire ZIP into a writable folder and try again.
  pause
)
