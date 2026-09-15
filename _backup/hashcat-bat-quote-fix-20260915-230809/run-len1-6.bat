@echo off
setlocal EnableExtensions

call "%~dp0resolve-hashcat.bat"
if errorlevel 1 exit /b 1

set "DIR=%~dp0"
cd /d "%DIR%"

"%HASHCAT_EXE%" -m 1500 -a 3 "%DIR%hash.txt" -1 ?l?d --increment --increment-min 1 --increment-max 6 ?1?1?1?1?1?1 --session endoscope_molink_len1_6 --potfile-path "%DIR%hashcat-endoscope.potfile" --outfile "%DIR%hashcat-found.txt" --outfile-format 2 --status --status-timer 10 -w 3 -O
pause
