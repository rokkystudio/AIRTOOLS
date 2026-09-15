@echo off
setlocal EnableExtensions

call 
"
%~dp0resolve-hashcat.bat
"
if errorlevel 1 exit /b 1

set 
"
DIR=%~dp0
"
cd /d 
"
%DIR%
"

"%HASHCAT_EXE%" -m 1500 "%DIR%hash.txt" --potfile-path "%DIR%hashcat-endoscope.potfile" --show  echo. echo Plaintext-only file: echo %DIR%hashcat-found.txt echo. if exist "%DIR%hashcat-found.txt" type "%DIR%hashcat-found.txt" pause
