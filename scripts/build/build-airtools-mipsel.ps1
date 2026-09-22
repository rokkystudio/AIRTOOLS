$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
& (Join-Path $root 'scripts\build\prepare-llvm.ps1')
$clang = Join-Path $root 'toolchain\llvm\mingw64\bin\clang.exe'
$out = Join-Path $root 'artifacts\binaries\mipsel\airtools_mipsel'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $out) | Out-Null
& $clang `
    --target=mipsel-linux-gnu `
    -march=mips32r2 `
    -mno-abicalls `
    -fno-pic `
    -G 0 `
    -Os `
    -ffreestanding `
    -fno-builtin `
    -nostdlib `
    -static `
    -fuse-ld=lld `
    "-Wl,-e,_start" `
    "-Wl,--build-id=none" `
    "-Wl,--gc-sections" `
    (Join-Path $root 'src\airtools\airtools.c') `
    (Join-Path $root 'src\airtools\mips_o32_syscalls.S') `
    -o $out
if ($LASTEXITCODE -ne 0) { throw "airtools build failed: $LASTEXITCODE" }
Get-Item $out | Select-Object FullName,Length
Get-FileHash $out -Algorithm SHA256