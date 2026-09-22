# Toolchain

Каталог `toolchain` содержит проверенные зависимости, необходимые для воспроизводимой сборки и исследования прошивки ENDOSCOPE. Они хранятся в репозитории вместе с проектом.

## Структура

```text
toolchain\
├── README.md
├── llvm\
│   └── mingw64\
│       ├── bin\
│       └── lib\clang\22\include\
├── lzma920\
└── uboot-mt7628-src\
```

## LLVM / Clang / LLD

MIPS binaries собираются Windows-сборкой Clang/LLD из MSYS2 MINGW64.

Проверенная версия:

```text
Clang 22.1.7
LLD   22.1.7
MSYS2 MINGW64
```

В репозитории хранится минимальный runtime вместо полного дерева MSYS2. Он содержит `clang.exe`, `ld.lld.exe`, необходимые DLL и Clang resource headers. Большая `libLLVM-22.dll` хранится как ZIP-архив `bin\libLLVM-22.dll.zip`; перед сборкой `scripts\build\prepare-llvm.ps1` автоматически распаковывает его в `bin`, получая `libLLVM-22.dll`. Распакованный DLL находится в `.gitignore`. Этот набор проверен реальной сборкой `aireplay_mipsel`, `airodump_mipsel` и `endoscope-connectivity`.

Build scripts ожидают компилятор по пути:

```text
toolchain\llvm\mingw64\bin\clang.exe
```

## LZMA SDK 9.20

`toolchain\lzma920` содержит legacy LZMA SDK 9.20. Он нужен для упаковки firmware в формат, совместимый с U-Boot устройства. Использовать:

```text
toolchain\lzma920\lzma.exe
```

Ожидаемая версия:

```text
LZMA 9.20 : Igor Pavlov : Public domain : 2010-11-18
```

## U-Boot source

`toolchain\uboot-mt7628-src` содержит сохраненный snapshot исходников U-Boot для MT7628. Текущая сборка `mtd4` от него не зависит, но snapshot хранится в репозитории для анализа bootloader и воспроизводимости исследований устройства.