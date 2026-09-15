@echo off
setlocal EnableExtensions

rem Resolve hashcat.exe without hard-coded absolute path.
rem Preferred: set HASHCAT_DIR to a folder that contains hashcat.exe.
rem Or add hashcat.exe to PATH.

set 
"
RESOLVED_HASHCAT=
"

if defined HASHCAT_DIR (
  if exist 
"
%HASHCAT_DIR%\hashcat.exe
"
 set 
"
RESOLVED_HASHCAT=%HASHCAT_DIR%\hashcat.exe
"
)

if not defined RESOLVED_HASHCAT (
  for %%I in (hashcat.exe) do set 
"
PATH_HASHCAT=%%~$PATH:I
"
  if defined PATH_HASHCAT set 
"
RESOLVED_HASHCAT=%PATH_HASHCAT%
"
)

if not defined RESOLVED_HASHCAT (
  if exist 
"
%~dp0hashcat.exe
"
 set 
"
RESOLVED_HASHCAT=%~dp0hashcat.exe
"
)

if not defined RESOLVED_HASHCAT (
  if exist 
"
%~dp0..\tools\hashcat-6.2.6\hashcat.exe
"
 set 
"
RESOLVED_HASHCAT=%~dp0..\tools\hashcat-6.2.6\hashcat.exe
"
)

if not defined RESOLVED_HASHCAT (
  echo ERROR: hashcat.exe not found.
  echo.
  echo Set HASHCAT_DIR to the folder containing hashcat.exe, for example:
  echo   set HASHCAT_DIR=C:\path\to\hashcat-6.2.6
  echo.
  echo Or add hashcat.exe to PATH.
  echo.
  pause
  exit /b 1
)

endlocal & set 
"
HASHCAT_EXE=%RESOLVED_HASHCAT%
"
exit /b 0
