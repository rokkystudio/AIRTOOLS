$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& (Join-Path $root 'scripts\build\build-airodump-mipsel.ps1')
& (Join-Path $root 'scripts\build\build-aireplay-mipsel.ps1')

& (Join-Path $root 'scripts\build\build-airtools-mipsel.ps1')
