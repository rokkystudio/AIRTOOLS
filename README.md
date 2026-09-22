# AIRTOOLS

Рабочий репозиторий по исследованию и модификации Wi-Fi эндоскопа на MT7628.

## Главные документы

- [DEVICE.md](DEVICE.md) - паспорт платы и текущее состояние проекта.
- [FIRMWARE.md](FIRMWARE.md) - сборка и прошивка текущего `mtd4`.
- [BRICK.md](BRICK.md) - как не закирпичить устройство, flash safety и recovery.
- [MONITOR.md](MONITOR.md) - актуальная monitor-архитектура: MT7628 AP + WN723N/RTL8188EUS monitor.
- [AIRTOOLS.md](AIRTOOLS.md) - текущая airtools-платформа, control API, target scan и handshake storage.
- [TODO.md](TODO.md) - незакрытые задачи и критерии готовности.
- [ARTIFACTS.md](ARTIFACTS.md) - сохранённые бинарники, драйверы и проверенные firmware artifacts.

Заводской Linux/software inventory лежит в [SYSTEM.md](SYSTEM.md). Доступы и Telnet-пароли отдельно: [CREDS.md](CREDS.md).

## Текущее рабочее состояние

Прошитый рабочий образ:

```text
dumps\verified\mtd4_airtools_mode_signal_20260923.bin
size:   3866624
sha256: 145413bdc96f95bcfe59c814f396ee1f0f45a4d3f8c6a08e37cf44e7de59c6ef
```

Устройство после загрузки:

```text
SSID: AT
Security: WPA2-Personal / CCMP
Password: 12345678
BSSID: e8:ab:fa:ae:6e:a1
Channel: 11
IP: 192.168.10.123
```

Проверено:

```text
boot OK
ping 192.168.10.123 OK
TCP 23 open
TCP 80 open
8188eu loaded
mt_wifi loaded
ra1 = AP/control
wlan0 = monitor, type 803
airtools TCP/8088 responds
```

## Структура проекта

```text
dumps\
  original\                 заводские/recovery dumps, не перезаписывать
  bases\                    стабильные base images для пересборки
  verified\                 проверенные прошитые images

artifacts\                  сохранённые бинарники, драйверы, Windows helpers
src\airtools\               исходники airtools/airodump/aireplay/runtime helpers
src\connectivity\           исходники и builder connectivity firmware
src\monitor\                старый ra1/ra0 monitor helper
external\                   сохраненный Linux archive и локальные сторонние исходники
toolchain\                  минимальный LLVM, LZMA 9.20 и U-Boot source
scripts\build\              firmware/tool builders
scripts\uart\               UART connect, RAM boot, recovery
scripts\wifi\               Wi-Fi/Telnet convenience helpers
scripts\tftp\               TFTP serving helpers
scripts\recovery\           CH341A recovery helpers
tools\CH341\               CH341A software, drivers and reference photos
scripts\telnet\             Telnet helpers and local config
images\                     фотографии платы
```

## Жесткое правило flash

Без отдельного решения не писать:

```text
mtd1 Bootloader
mtd2 Config
mtd3 Factory
```

Обычная рабочая модификация сейчас находится только в:

```text
mtd4 Kernel/rootfs
```

Перед любой записью во flash читать [BRICK.md](BRICK.md).
