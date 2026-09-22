$ErrorActionPreference = 'Stop'

$Root = 'D:\PROJECTS\AIRTOOLS'
& (Join-Path $Root 'scripts\build\prepare-llvm.ps1')
$SourceDir = Join-Path $Root 'src\connectivity'
$LlvmBin = Join-Path $Root 'toolchain\llvm\mingw64\bin'
$Clang = Join-Path $LlvmBin 'clang.exe'
$Output = Join-Path $Root 'artifacts\binaries\mipsel\endoscope-connectivity'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Output) | Out-Null

if (-not (Test-Path -LiteralPath $Clang)) {
    throw "clang.exe not found: $Clang"
}

$env:PATH = "$LlvmBin;C:\msys64\mingw64\bin;$env:PATH"

$Arguments = @(
    '--target=mipsel-linux-gnu'
    '-march=mips32r2'
    '-mabi=32'
    '-msoft-float'
    '-EL'
    '-Os'
    '-ffreestanding'
    '-fno-builtin'
    '-fno-stack-protector'
    '-fno-pic'
    '-mno-abicalls'
    '-G0'
    '-ffunction-sections'
    '-fdata-sections'
    '-nostdlib'
    '-static'
    '-fuse-ld=lld'
    '-Wl,-e,_start'
    '-Wl,--gc-sections'
    '-Wl,--build-id=none'
    '-o'
    $Output
    (Join-Path $SourceDir 'start.S')
    (Join-Path $SourceDir 'connectivity.c')
)

& $Clang @Arguments
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

$File = Get-Item -LiteralPath $Output
$Hash = Get-FileHash -LiteralPath $Output -Algorithm SHA256

Write-Host "daemon=$($File.FullName)"
Write-Host "bytes=$($File.Length)"
Write-Host "sha256=$($Hash.Hash)"
