@echo off
setlocal EnableExtensions

set "HOST=192.168.10.123"
set "PORT=23"

if not "%~1"=="" set "PORT=%~1"

set "ROOT=%~dp0.."
set "TOOLS=%ROOT%\tools"
set "PUTTY="

if exist "%ProgramFiles%\PuTTY\putty.exe" set "PUTTY=%ProgramFiles%\PuTTY\putty.exe"
if not defined PUTTY if exist "%ProgramFiles(x86)%\PuTTY\putty.exe" set "PUTTY=%ProgramFiles(x86)%\PuTTY\putty.exe"
if not defined PUTTY if exist "%TOOLS%\putty.exe" set "PUTTY=%TOOLS%\putty.exe"

if not defined PUTTY (
  echo PuTTY not found. Downloading portable putty.exe into:
  echo %TOOLS%
  if not exist "%TOOLS%" mkdir "%TOOLS%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; Invoke-WebRequest -Uri 'https://the.earth.li/~sgtatham/putty/latest/w64/putty.exe' -OutFile '%TOOLS%\putty.exe'"
  if exist "%TOOLS%\putty.exe" set "PUTTY=%TOOLS%\putty.exe"
)

if not defined PUTTY (
  echo ERROR: PuTTY was not found and could not be downloaded.
  pause
  exit /b 1
)

echo Connecting to ENDOSCOPE Telnet: %HOST%:%PORT%
echo Login: molink
echo Password: molinkad

"%PUTTY%" -telnet %HOST% %PORT%
