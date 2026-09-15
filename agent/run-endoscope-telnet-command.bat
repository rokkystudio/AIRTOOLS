@echo off
setlocal EnableExtensions

if "%~1"=="" (
  echo Usage:
  echo   %~nx0 "cat /proc/cpuinfo"
  echo.
  echo Edit first:
  echo   %~dp0endoscope-telnet.local.ps1
  exit /b 1
)

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0invoke-endoscope-telnet.ps1" -Command %*