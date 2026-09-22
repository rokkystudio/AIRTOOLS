@echo off
setlocal EnableExtensions

set "ROOT=%~dp0..\.."
set "PY=C:\Users\rokky\AppData\Local\Programs\Python\Python310\python.exe"

if not exist "%PY%" (
    echo ERROR: Python not found: %PY%
    exit /b 1
)

echo [1/3] Building MIPS connectivity daemon...
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\src\connectivity\build-daemon.ps1"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [2/3] Building modified mtd4...
"%PY%" "%ROOT%\src\connectivity\build-mtd4.py"
if errorlevel 1 exit /b %errorlevel%

echo.
echo [3/3] Running mandatory preflight...
"%PY%" "%ROOT%\src\connectivity\verify-mtd4.py"
if errorlevel 1 exit /b %errorlevel%

echo.
echo Firmware is ready for RAM-only test boot:
echo %ROOT%\dumps\modified\mtd4_connectivity.bin
echo.
echo DO NOT flash it persistently before scripts\uart\test-boot.py succeeds.
exit /b 0
