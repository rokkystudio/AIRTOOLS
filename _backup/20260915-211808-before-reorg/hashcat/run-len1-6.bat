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
"%HASHCAT%" -m 1500 -a 3 "%DIR%hash.txt" -1 ?l?d --increment --increment-min 1 --increment-max 6 ?1?1?1?1?1?1 --session endoscope_molink_len1_6 --potfile-path "%DIR%hashcat-endoscope.potfile" --outfile "%DIR%hashcat-found.txt" --outfile-format 2 --status --status-timer 10 -w 3 -O
pause
