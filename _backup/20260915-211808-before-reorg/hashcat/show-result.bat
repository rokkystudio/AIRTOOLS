@echo off
setlocal
set "HASHCAT=E:\AIRTOOLS\hashcat-6.2.6\hashcat.exe"
set "DIR=%~dp0"

if not exist "%HASHCAT%" (
  echo ERROR: hashcat.exe not found: %HASHCAT%
  pause
  exit /b 1
)

if not exist "%DIR%hash.txt" (
  echo ERROR: hash.txt not found in %DIR%
  pause
  exit /b 1
)

cd /d "%~dp0"
"%HASHCAT%" -m 1500 "%DIR%hash.txt" --potfile-path "%DIR%hashcat-endoscope.potfile" --show
echo.
echo Plaintext-only file, if created:
echo %DIR%hashcat-found.txt
echo.
if exist "%DIR%hashcat-found.txt" type "%DIR%hashcat-found.txt"
pause
