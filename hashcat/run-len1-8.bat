@echo off
setlocal EnableExtensions

rem Runs the ENDOSCOPE hash in mask mode for lengths 1 through 8.
rem HASHCAT_DIR may point to a folder containing hashcat.exe.
rem Otherwise hashcat.exe is resolved from PATH or this folder.

set "DIR=%~dp0"
set "HASHCAT_EXE="

if defined HASHCAT_DIR (
    if exist "%HASHCAT_DIR%\hashcat.exe" set "HASHCAT_EXE=%HASHCAT_DIR%\hashcat.exe"
)

if not defined HASHCAT_EXE (
    for %%I in (hashcat.exe) do set "HASHCAT_EXE=%%~$PATH:I"
)

if not defined HASHCAT_EXE (
    if exist "%DIR%hashcat.exe" set "HASHCAT_EXE=%DIR%hashcat.exe"
)

if not defined HASHCAT_EXE (
    echo ERROR: hashcat.exe not found.
    echo Set HASHCAT_DIR or add hashcat.exe to PATH.
    pause
    exit /b 1
)

cd /d "%DIR%"

"%HASHCAT_EXE%" ^
    -m 1500 ^
    -a 3 ^
    "%DIR%hash.txt" ^
    -1 ?l?d ^
    ?1?1?1?1?1?1?1?1 ^
    --increment ^
    --increment-min 1 ^
    --increment-max 8 ^
    --session endoscope_molink_len1_8 ^
    --potfile-path "%DIR%hashcat-endoscope.potfile" ^
    --outfile "%DIR%hashcat-found.txt" ^
    --outfile-format 2 ^
    --status ^
    --status-timer 10 ^
    -w 3

echo.
if exist "%DIR%hashcat-found.txt" (
    echo Result file:
    type "%DIR%hashcat-found.txt"
)

echo.
pause
