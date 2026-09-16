# ENDOSCOPE

Проект исследования и модификации Wi-Fi эндоскопа на MT7628.

## Документация

- [DEVICE.md](DEVICE.md) — характеристики конкретного экземпляра.
- [SYSTEM.md](SYSTEM.md) — общая карта Linux и прошивки.
- [FIRMWARE.md](FIRMWARE.md) — сборка, RAM test boot, flash и recovery.
- [CREDS.md](CREDS.md) — данные доступа и восстановление Telnet.
- [TONY.md](TONY.md) — заметки по внешней статье о похожем устройстве.

## Структура проекта

```text
dumps\
  original\                 неизменяемые заводские flash/MTD dumps
  modified\                 готовые модифицированные partition images

services\connectivity\      исходник и сборка локального DNS/HTTP daemon
toolchain\llvm\             MIPS cross compilation
toolchain\lzma920\          legacy LZMA encoder/decoder
scripts\                     build, UART, recovery
agent\                       Telnet automation
images\                      фотографии платы
hashcat\                     сохранённые hashcat-файлы
```

## Заводской backup

```text
dumps\original\flash_full_mtd0.bin
dumps\original\mtd1_bootloader.bin
dumps\original\mtd2_config.bin
dumps\original\mtd3_factory.bin
dumps\original\mtd4_kernel.bin
```

`dumps\original` не должен изменяться сборочными или flash-скриптами.

## Сборка modified firmware

```powershell
scripts\build-firmware.bat
```

Сборка выполняет:

1. MIPS-компиляцию `endoscope-connectivity`;
2. сборку `mtd4_connectivity.bin`;
3. обязательный firmware preflight.

Успешный результат должен содержать:

```text
PRELIGHT OK
```

Готовый образ:

```text
dumps\modified\mtd4_connectivity.bin
```

## Безопасный порядок обновления

Новый modified image **не записывается сразу во flash**.

Сначала обязательный RAM-only boot:

```powershell
python scripts\uart-test-boot.py --image dumps\modified\mtd4_connectivity.bin --boot
```

U-Boot загружает uImage по UART в RAM и выполняет `bootm`. SPI flash этим тестом не изменяется.

Только после успешного RAM boot и проверки нужных сервисов допускается запись `mtd4`.

Подробно: [FIRMWARE.md](FIRMWARE.md).

## UART recovery

Параметры:

```text
COM3
57600 8N1
flow control: none
```

Подключение:

```text
CP2102 GND -> GND
CP2102 RXD -> T
CP2102 TXD -> R
питание с CP2102 не подключать
```

Загрузка заводской прошивки только в RAM:

```powershell
python scripts\uart-test-boot.py --image dumps\original\mtd4_kernel.bin --boot
```

Это основной recovery-путь перед любой постоянной записью.

## Wi-Fi / Telnet

После нормальной загрузки системы:

```powershell
scripts\connect-endoscope-wifi.bat
```

Одна Telnet-команда:

```powershell
agent\run-endoscope-telnet-command.bat "cat /proc/cpuinfo"
```

Локальные параметры Telnet находятся в:

```text
agent\endoscope-telnet.local.ps1
```

## UART terminal

```powershell
scripts\connect-endoscope-uart.bat
```

Для другого COM-порта:

```powershell
scripts\connect-endoscope-uart.bat COM4
```

## Текущий recovery

Текущий flash `mtd4` содержит предыдущую тестовую сборку, которую U-Boot не может распаковать.

Причина определена: внешний LZMA stream был создан в формате с неизвестным unpacked size. Исправленная сборка использует legacy LZMA SDK 9.20 и проходит обязательный preflight.

Recovery выполняется через UART с заводским `dumps\original\mtd4_kernel.bin`, загружаемым сначала только в RAM.
