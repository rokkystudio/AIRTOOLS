@echo off
setlocal
set "COMPORT=COM3"
if not "%~1"=="" set "COMPORT=%~1"
if exist "%ProgramFiles%\PuTTY\putty.exe" (
  "%ProgramFiles%\PuTTY\putty.exe" -serial %COMPORT% -sercfg 57600,8,n,1,N
  exit /b
)
if exist "%ProgramFiles(x86)%\PuTTY\putty.exe" (
  "%ProgramFiles(x86)%\PuTTY\putty.exe" -serial %COMPORT% -sercfg 57600,8,n,1,N
  exit /b
)
echo PuTTY not found.
echo Install PuTTY or put putty.exe into Program Files.
pause
