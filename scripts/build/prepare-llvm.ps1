$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$Bin = Join-Path $Root 'toolchain\llvm\mingw64\bin'
$Dll = Join-Path $Bin 'libLLVM-22.dll'
$Archive = Join-Path $Bin 'libLLVM-22.dll.zip'

if (Test-Path -LiteralPath $Dll) {
    exit 0
}

if (-not (Test-Path -LiteralPath $Archive)) {
    throw "LLVM runtime archive not found: $Archive"
}

Write-Host 'Extracting libLLVM-22.dll from toolchain archive...'
Expand-Archive -LiteralPath $Archive -DestinationPath $Bin -Force

if (-not (Test-Path -LiteralPath $Dll)) {
    throw "LLVM runtime extraction failed: $Dll"
}