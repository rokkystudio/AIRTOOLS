# ENDOSCOPE firmware workflow

## Каталоги образов

Заводские дампы хранятся только в:

```text
dumps\original\
```

Эти файлы являются recovery-копией и не должны перезаписываться сборочными или flash-скриптами.

Готовые модифицированные partition images хранятся только в:

```text
dumps\modified\
```

Текущий модифицированный образ:

```text
dumps\modified\mtd4_connectivity.bin
```

## Сборка

Использовать только:

```powershell
scripts\build-firmware.bat
```

Сценарий выполняет три обязательных шага:

1. собирает `endoscope-connectivity` под MIPS32EL;
2. пересобирает `mtd4` с legacy LZMA SDK 9.20;
3. запускает `verify-mtd4.py`.

Образ не считается готовым, пока проверка не закончилась строкой:

```text
PRELIGHT OK
```

Preflight проверяет размер partition, uImage CRC, оба LZMA-слоя, совместимость их заголовков с заводским образом, неизменность kernel layout и сохранённой области flash.

## Обязательный RAM test boot

Новый `mtd4` нельзя сразу записывать во flash.

Сначала он должен успешно загрузиться только из RAM через U-Boot:

```powershell
python scripts\uart-test-boot.py --image dumps\modified\mtd4_connectivity.bin --boot
```

Сценарий:

1. повторно выполняет preflight;
2. входит в U-Boot CLI через UART;
3. загружает uImage в RAM по Kermit;
4. выполняет `bootm`;
5. не выполняет ни одной команды записи SPI flash.

Только образ, который реально загрузился из RAM и прошёл проверку нужных сервисов, допускается к постоянной записи.

## Recovery

UART:

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
питание CP2102 не подключать
```

Для восстановления сначала загружается заводской образ только в RAM:

```powershell
python scripts\uart-test-boot.py --image dumps\original\mtd4_kernel.bin --boot
```

После успешной загрузки заводского Linux можно восстановить `mtd4` из:

```text
dumps\original\mtd4_kernel.bin
```

Постоянную запись выполнять только с UART, подключённым как recovery-канал.

## Правила flash

- Никогда не изменять `mtd1`, `mtd2` или `mtd3` при обновлении Linux.
- Для Linux использовать только `mtd4`.
- Не прошивать файл, который не прошёл `verify-mtd4.py`.
- Не прошивать modified image, который не прошёл RAM test boot.
- Flash-операция и reboot должны быть раздельными действиями.
- После записи сначала проверить код возврата и UART, только затем перезагружать.
- `dumps\original` всегда сохранять неизменным.

## Почему используется LZMA SDK 9.20

U-Boot этого устройства ожидает legacy `.lzma` header с явным размером распакованных данных.

Сборщик поэтому использует:

```text
toolchain\lzma920\lzma.exe
```

для обоих LZMA-слоёв:

1. initramfs внутри kernel;
2. полный kernel внутри U-Boot uImage.

Современный LZMA stream с неизвестным unpacked size для этого U-Boot не считается совместимым.
