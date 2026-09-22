# AIRTOOLS Firmware Workflow

Этот файл описывает текущий рабочий путь для `mtd4` firmware. Bootloader/config/factory не являются частью обычного firmware update. Правила безопасности flash/recovery находятся в [BRICK.md](BRICK.md).

## Текущий рабочий образ

```text
path:   dumps\verified\mtd4_airtools_mode_signal_20260923.bin
size:   3866624
sha256: 145413bdc96f95bcfe59c814f396ee1f0f45a4d3f8c6a08e37cf44e7de59c6ef
```

Этот образ прошит и проверен. После reboot U-Boot распаковал uImage, checksum прошел, Linux стартовал.

## Что внутри

```text
ra1 AP/control:
  SSID: AT
  auth: WPA2PSK / AES
  password: 12345678
  IP: 192.168.10.123

wlan0 monitor:
  adapter: TP-Link WN723N / RTL8188EUS
  driver: 8188eu
  mode: Monitor
  type: 803
  channel: 11

runtime payload:
  /bin/airtools
  /bin/airwifi
  /bin/airodump
  /bin/aireplay
  /bin/wn723n-monitor
  /bin/wn723n-extract
```

## Сборка

Основной builder текущего WN723N/airtools образа:

```powershell
python scripts\build\build-mtd4-airtools.py
```

Builder пишет новый образ в disposable-каталог:

```text
dumps\modified\
```

Проверенный руками образ нужно продвигать в:

```text
dumps\verified\
```

Старый общий wrapper тоже существует:

```powershell
scripts\build\build-firmware.bat
```

После сборки обязательно проверить:

```text
size == 3866624
uImage header CRC OK
uImage data CRC OK
rootfs payload contains airtools/airwifi/airodump/aireplay
```

## Прошивка mtd4

Писать только раздел `Kernel` / `mtd4`.

Проверенный результат последней прошивки:

```text
TFTP_RET:0
mtd4_wn723n.bin size=3866624
mtd_write target: mtd4 "Kernel"
MTD_WRITE_RET:0
SYNC_DONE
U-Boot Data Size: 2946383 Bytes
Verifying Checksum ... OK
LINUX started
```

Практические требования:

- UART подключен до записи и остается подключенным до успешной загрузки.
- TFTP transfer проверен по размеру.
- `mtd_write` пишет только `Kernel`.
- Reboot выполняется только после `MTD_WRITE_RET:0` и `SYNC_DONE`.
- После загрузки проверяются Wi-Fi, telnet/http и airtools TCP.

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

Оригинальные recovery-копии хранятся в:

```text
dumps\original\
```

`dumps\original` не перезаписывать сборочными или flash-скриптами.

## LZMA note

U-Boot этого устройства ожидает legacy `.lzma` header с явным размером распакованных данных. Современный LZMA stream с unknown unpacked size может дать:

```text
Uncompressing Kernel Image ... LZMA ERROR 1
```

Поэтому при сборке `mtd4` проверять не только uImage header, но и фактическую распаковку payload.
