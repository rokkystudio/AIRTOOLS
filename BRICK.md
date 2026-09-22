# Как Не Закирпичить

Короткая рабочая инструкция по flash/recovery для этого MT7628 эндоскопа.

## Главное Правило

Обычная разработка и обновление идут только через:

```text
mtd4 Kernel/rootfs
```

Без отдельного осознанного решения не писать:

```text
mtd1 Bootloader
mtd2 Config
mtd3 Factory
```

Текущий проверенный `mtd4`:

```text
dumps\verified\mtd4_at_wpa2_airtools_wn723n_20260920.bin
size:   3866624
sha256: 7443772442fbbc038305f75659d8b628b319b1da73f99f699a43904f8271124d
```

Known-good bootloader:

```text
dumps\original\mtd1_bootloader.bin
size:   196608
sha256: 9012c77628e5a7724d7fea2641399978089445cfc655671ee872741725ca31b6
```

## Перед Записью mtd4

Проверить:

- UART подключен и виден boot log.
- Image size ровно `0x3B0000` / `3866624`.
- Пишем target `Kernel`, не `Bootloader`.
- uImage header CRC и data CRC OK.
- LZMA payload реально распаковывается.
- TFTP transfer на устройстве совпадает по размеру.

Ожидаемый результат записи:

```text
MTD_WRITE_RET:0
SYNC_DONE
```

Ожидаемый reboot:

```text
Verifying Checksum ... OK
LINUX started
```

Smoke test после загрузки:

```text
ping 192.168.10.123
TCP_23 open
TCP_80 open
/status over UDP/8088
/wifi/status over UDP/8088
wlan0 type == 803
```

## Случай 1: Неверный mtd4 / LZMA

Симптом:

```text
3: System Boot system code via Flash.
Uncompressing Kernel Image ... LZMA ERROR 1 - must RESET board to recover
```

Причина: uImage header был формально валидный, но LZMA stream был несовместим с U-Boot устройства. Для этого U-Boot нужен legacy `.lzma` stream с явным unpacked size.

Как не повторить:

- Не считать uImage header достаточной проверкой.
- Проверять оба CRC.
- Проверять реальную распаковку LZMA.
- Использовать `toolchain\lzma920\lzma.exe`.
- Новый image сначала проверять как файл, затем писать только `mtd4`.

Recovery: вернуть заводской или проверенный `mtd4` через UART/CH341A, если Linux не грузится.

## Случай 2: Экспериментальный mtd1

Симптом:

```text
RESET MT7628 PHY!!!!!!default: 3
```

После этого Linux/Wi-Fi не поднимаются.

Причина: был прошит экспериментальный bootloader patch. Ошибка была в runtime relocation: абсолютный MIPS `j` выглядел нормально в static disassembly, но после relocation U-Boot прыгал не туда.

Как не повторить:

- Не патчить `mtd1` ради обычной разработки.
- Не использовать абсолютный MIPS `j` в relocated U-Boot code без доказательства адресного сегмента.
- Не писать `mtd1` без свежего readback текущего `mtd1` и byte/sha сравнения.
- Перед любым bootloader test иметь готовый direct CH341A recovery.

Recovery, который сработал: direct/desoldered CH341A restore оригинального `mtd1_bootloader.bin`. После возврата SHA `9012...31b6` U-Boot, Linux и Wi-Fi восстановились.

## Случай 3: mtd2 Config

Для этого устройства нормально:

```text
*** Warning - bad CRC, using default environment
```

`mtd2` может быть factory-blank. Не нужно писать валидный U-Boot env только чтобы убрать warning или выставить `BootType=3`.

Как не повторить:

- Не писать `mtd2` без отдельной причины.
- Не считать bad CRC env ошибкой.
- Не хранить runtime настройки airtools в `mtd2/mtd3` без отдельного persistence-дизайна.

## CH341A

In-circuit CH341A на этой плате был ненадежен: встречались all-FF и нестабильные reads.

Доверять только при стабильном JEDEC:

```text
EF 40 16
```

Direct/desoldered W25Q32BV был стабильным и восстановил `mtd1`.

Pinout:

```text
1 CS#       -> CH341 CS
2 DO/MISO   -> CH341 MISO
3 WP#       -> 3.3V/high
4 GND       -> CH341 GND
5 DI/MOSI   -> CH341 MOSI
6 CLK       -> CH341 CLK
7 HOLD#     -> 3.3V/high
8 VCC       -> 3.3V
```

## Минимальный Безопасный Порядок

1. Сначала понять, какой раздел нужен.
2. Для firmware писать только `mtd4`.
3. Проверить size/hash/CRC/LZMA.
4. Держать UART подключенным.
5. После записи дождаться `SYNC_DONE`.
6. После reboot проверить boot, сеть и airtools.
7. `mtd1/mtd2/mtd3` не трогать, пока нет отдельного recovery-плана.
