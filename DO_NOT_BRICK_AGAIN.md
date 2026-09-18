# Как больше не кирпичить эндоскоп

## Что произошло

Устройство было закирпичено после записи неверного `mtd4`-образа. Заголовок `uImage` был формально валидный, но LZMA-поток не загружался, поэтому U-Boot уходил в цикл:

```text
3: System Boot system code via Flash.
Uncompressing Kernel Image ... LZMA ERROR 1 - must RESET board to recover
```

Проблему усугубило то, что U-Boot по умолчанию выбирал пункт `3`, то есть автоматическую загрузку из flash. Вход в меню по UART был ненадёжный, поэтому пришлось читать SPI flash программатором CH341A.

## Что подтвердил CH341A dump

Сравнение сохранено здесь:

```text
D:\PROJECTS\ENDOSCOPE\dumps\ch341\flash_full_ch341_20260917-211155.compare.md
```

Прочитанный dump:

```text
D:\PROJECTS\ENDOSCOPE\dumps\ch341\flash_full_ch341_20260917-211155.bin
size:   4194304
sha256: E172F4CB8DD6AE7FD461EB9788A08D521EED31D8EE3000934E28B47467676B75
```

Сравнение с оригинальным полным dump:

| Раздел | Offset | Size | Результат |
|---|---:|---:|---|
| `mtd1_bootloader` | `0x000000` | `0x030000` | совпадает с оригиналом |
| `mtd2_config` | `0x030000` | `0x010000` | совпадает с оригиналом |
| `mtd3_factory` | `0x040000` | `0x010000` | совпадает с оригиналом |
| `mtd4_kernel` | `0x050000` | `0x3B0000` | отличается |

Вывод: bootloader/config/factory целые. Повреждён только `mtd4`.

## Обязательные проверки перед любой записью во flash

1. Перед записью должен быть полный backup 4 MiB и SHA256.
2. Не писать bootloader (`0x000000..0x02FFFF`), если нет отдельной проверенной причины.
3. Для обычного восстановления писать только `mtd4`: offset `0x50000`, длина `0x3B0000`.
4. Проверить, что образ помещается в раздел и правильно допадден до размера раздела.
5. Проверить `uImage` header:
   - magic: `0x27051956`
   - load: `0x80000000`
   - entry: `0x8000C150`
   - compression: `3` / LZMA
6. Проверить не только header CRC, но и data CRC.
7. До прошивки обязательно сделать dry-run распаковки LZMA payload.
8. Если возможно, сначала загрузить образ в RAM через U-Boot `loadb`/`bootm`, и только потом писать во flash.
9. При работе через CH341A читать минимум два раза и сравнивать SHA256.
10. Не доверять чтению CH341A, пока JEDEC ID не стабилен:

```text
EF 40 16
```

## CH341A / W25Q32BV подключение

SOIC-8 W25Q32BV / 25Q32:

```text
          точка / ключ
      1  CS#          VCC   8
      2  DO / MISO    HOLD# 7
      3  WP#          CLK   6
      4  GND          DI/MOSI 5
```

Подключение:

```text
pin 1 CS#    -> CH341 CS
pin 2 DO     -> CH341 MISO
pin 3 WP#    -> 3.3V / high
pin 4 GND    -> CH341 GND
pin 5 DI     -> CH341 MOSI
pin 6 CLK    -> CH341 CLK
pin 7 HOLD#  -> 3.3V / high
pin 8 VCC    -> 3.3V
```

Если при подключении прищепки плата оживает, а CH341A отваливается, остановиться. Это значит, что программатор питает всю плату или есть просадка/короткое. Нельзя продолжать запись до устранения.

## Исправление U-Boot: default `4`, а не `3`

Исправлен исходник:

```text
D:\PROJECTS\ENDOSCOPE\toolchain\uboot-mt7628-src\src\lib_mips\board.c
```

Backup исходника до патча:

```text
D:\PROJECTS\ENDOSCOPE\toolchain\uboot-mt7628-src\src\lib_mips\board.c.before-default-cli.patch
```

Patch file:

```text
D:\PROJECTS\ENDOSCOPE\toolchain\uboot-mt7628-src\patches\default_cli_boottype4.patch
```

Изменения:

```c
unsigned char BootType='3', confirm=0;
```

заменено на:

```c
unsigned char BootType='4', confirm=0; /* patched: default to CLI, not flash boot */
```

И fallback при неверном выборе меню:

```c
BootType = '3';
```

заменён на:

```c
BootType = '4'; /* patched: invalid menu input falls back to CLI */
```

Ожидаемое поведение после сборки и прошивки проверенного bootloader: при старте без успешного выбора меню U-Boot должен попадать в CLI (`MT7628 #`), а не автоматически выбирать `3` и грузить битый kernel из flash.

Важно: бинарный bootloader пока не пересобран и не прошит. На этом ПК не найден MIPS toolchain `mipsel-linux-gcc`; бинарный patch bootloader вслепую не делать.

## Текущая безопасная цель восстановления

Проверенный оригинальный `mtd4`:

```text
D:\PROJECTS\ENDOSCOPE\dumps\original\mtd4_kernel.bin
sha256: 72904FD990D724D81CF2EBD3C1E812954C55422442D16CAB7C0E152FF3610C2D
```

Целевой адрес для восстановления:

```text
flash offset: 0x50000
length:       0x3B0000
```

Если пишем весь чип программатором, безопаснее использовать оригинальный полный dump:

```text
D:\PROJECTS\ENDOSCOPE\dumps\original\flash_full_mtd0.bin
sha256: C11AD67DE1A32884BE18A00655CAA75FE0CB883520F1F422A629009DA72E3967
```
