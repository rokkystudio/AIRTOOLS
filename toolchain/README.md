# Toolchain

Каталог `toolchain` содержит локальные зависимости сборки. В Git хранится только этот файл; скачанные компиляторы, SDK и сторонние исходники остаются локальными.

## Ожидаемая структура

```text
toolchain\
├── README.md
├── llvm\
│   └── mingw64\
│       └── bin\
│           ├── clang.exe
│           └── ld.lld.exe
└── lzma920\
    └── lzma.exe
```

## LLVM / Clang / LLD

Сборка `services\connectivity\build-daemon.ps1` использует Windows-сборку Clang и LLD из MSYS2 MINGW64.

Проверенная конфигурация проекта:

```text
Clang 22.1.7
LLD   22.1.7
MSYS2 MINGW64
```

MSYS2:

```text
https://www.msys2.org/
```

Установить MSYS2 в стандартный каталог:

```text
C:\msys64
```

В терминале `MSYS2 MINGW64` установить Clang и LLD:

```bash
pacman -Syu
pacman -S --needed mingw-w64-x86_64-clang mingw-w64-x86_64-lld
```

Из корня проекта скопировать MINGW64 runtime в локальный `toolchain`:

```powershell
New-Item -ItemType Directory -Force .\toolchain\llvm | Out-Null
Copy-Item C:\msys64\mingw64 .\toolchain\llvm\mingw64 -Recurse
```

Проверка:

```powershell
.\toolchain\llvm\mingw64\bin\clang.exe --version
Test-Path .\toolchain\llvm\mingw64\bin\ld.lld.exe
```

`build-daemon.ps1` ожидает Clang именно по пути:

```text
toolchain\llvm\mingw64\bin\clang.exe
```

## LZMA SDK 9.20

Для упаковки firmware требуется legacy LZMA SDK 9.20. Эта версия создаёт формат, совместимый с U-Boot устройства.

Официальный архив 7-Zip:

```text
https://www.7-zip.org/a/lzma920.tar.bz2
```

Архив двухслойный: `bz2 -> tar -> файлы SDK`. Для распаковки удобно использовать установленный 7-Zip.

Из корня проекта выполнить в PowerShell:

```powershell
$Archive = Join-Path $env:TEMP 'lzma920.tar.bz2'
$Extract = Join-Path $env:TEMP 'lzma920'

Remove-Item $Extract -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $Extract | Out-Null
New-Item -ItemType Directory -Force .\toolchain\lzma920 | Out-Null

Invoke-WebRequest 'https://www.7-zip.org/a/lzma920.tar.bz2' -OutFile $Archive
& 'C:\Program Files\7-Zip\7z.exe' x $Archive "-o$Extract" -y
& 'C:\Program Files\7-Zip\7z.exe' x (Join-Path $Extract 'lzma920.tar') "-o$PWD\toolchain\lzma920" -y

Remove-Item $Archive -Force
Remove-Item $Extract -Recurse -Force
```

Проверка:

```powershell
Test-Path .\toolchain\lzma920\lzma.exe
```

Ожидаемая версия:

```text
LZMA 9.20 : Igor Pavlov : Public domain : 2010-11-18
```

## U-Boot source

`uboot-mt7628-src` текущей сборкой проекта не используется и для работы `scripts\build-firmware.bat` не требуется. Его не нужно размещать в `toolchain`.

Если исходники U-Boot понадобятся для отдельного исследования, их следует клонировать отдельно от зависимостей, которые хранит основной репозиторий.
