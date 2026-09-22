$ErrorActionPreference = 'Stop'
$root = 'D:\PROJECTS\ENDOSCOPE'
& (Join-Path $root 'scripts\build\build-airodump-mipsel.ps1')
& (Join-Path $root 'scripts\build\build-aireplay-mipsel.ps1')
