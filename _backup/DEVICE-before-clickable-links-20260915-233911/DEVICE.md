# ENDOSCOPE: характеристики нашего устройства

Этот файл содержит только то, что было получено на нашем экземпляре через фото, UART, Windows/USB/Wi-Fi проверки и локальные логи проекта.

## Источники внутри проекта

```text
images\
logs\uart-20260915-200900-57600.txt
logs\uart-20260915-200900-57600.bin
logs\uart-shell-20260915-201108.txt
logs\uart-readonly-20260915-201154.txt
```

## Плата

По фотографиям платы:

```text
ML-7066 REV:3.0
2018-10-18
```

Фотографии лежат в:

```text
images\1789487224941.jpg
images\1789487224948.jpg
images\1789489367549.jpg
images\1789499849818.jpg
```

## Test pads и UART

Найденные площадки:

```text
GND          земля
R / T        UART RX/TX
TXN/TXP      дифференциальная пара, не UART
RXN/RXP      дифференциальная пара, не UART
SDA/CLK      назначение требует отдельной проверки
```

Подключение CP2102/USB-UART:

```text
CP2102 GND -> GND на плате
CP2102 RXD -> T на плате
CP2102 TXD -> R на плате
Питание 5V/3V3 с CP2102 не подключать
```

Параметры UART:

```text
COM3, 57600 8N1, flow control: none
```

Подключение:

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat
```

## USB

USB-подключение самого эндоскопа к Windows не дало нового PnP-устройства. По результату этой проверки USB не рассматривается как подтверждённый data-интерфейс.

CP2102 USB-UART определился отдельно как:

```text
Silicon Labs CP210x USB to UART Bridge (COM3)
VID_10C4&PID_EA60
```

## Wi-Fi и сеть

Наш компьютер был подключен к AP устройства:

```text
SSID: ENDOSCOPE
PC IP: 192.168.10.36/24
device/gateway IP: 192.168.10.123
BSSID/MAC: E8:AB:FA:AE:6E:A1
channel: 11
```

ARP подтвердил устройство по адресу `192.168.10.123` с MAC `E8-AB-FA-AE-6E-A1`.

Проверенные TCP-порты:

```text
23/tcp   open    Telnet, banner: MoLink login:
7060/tcp open    нестандартный сервис, вероятно video/app service
22/tcp   closed  SSH недоступен
```

## Boot log

Основной boot log:

```text
logs\uart-20260915-200900-57600.txt
logs\uart-20260915-200900-57600.bin
```

Файл `uart-20260915-200900-57600.bin` — это бинарный UART-захват, а не дамп flash. Такие файлы остаются в `logs\`.

Из boot log нашего устройства:

```text
U-Boot 1.1.3 (Aug  9 2018 - 17:34:36)
Board: Ralink APSoC DRAM:  64 MB
Ralink UBoot Version: 5.0.0.0
ASIC 7628_MP
CPU freq = 580 MHZ
find flash: W25Q32BV
BusyBox v1.23.0 (2018-03-30 18:02:20 CST)
starting pid 249, tty '/dev/ttyS1': '/bin/sh'
```

После загрузки через UART доступен shell prompt:

```text
#
```

UART даёт shell без штатного Telnet-входа.

## Linux

Команды shell сохранены здесь:

```text
logs\uart-shell-20260915-201108.txt
logs\uart-readonly-20260915-201154.txt
```

CPU из `/proc/cpuinfo`:

```text
system type : MT7628
cpu model   : MIPS 24Kc V5.5
```

Процессы, которые видели в `ps`, включали:

```text
init
nvram_daemon
app_detect
app_cam
udhcpd /etc_ro/udhcpd.conf
telnetd
/bin/sh
```

## Flash

SPI flash из boot log:

```text
model: W25Q32BV
manufacturer id: ef
device id: 40 16
size: 4 MiB
```

Разметка flash из `/proc/mtd`:

| dev  | size     | erasesize | name       |
|------|----------|-----------|------------|
| mtd0 | 00400000 | 00010000  | ALL        |
| mtd1 | 00030000 | 00010000  | Bootloader |
| mtd2 | 00010000 | 00010000  | Config     |
| mtd3 | 00010000 | 00010000  | Factory    |
| mtd4 | 003b0000 | 00010000  | Kernel     |

Mount layout:

```text
rootfs on / type rootfs (rw)
proc on /proc type proc (rw,relatime)
none on /var type ramfs (rw,relatime)
none on /dev type ramfs (rw,relatime)
none on /etc type ramfs (rw,relatime)
none on /tmp type ramfs (rw,relatime)
none on /media type ramfs (rw,relatime)
none on /sys type sysfs (rw,relatime)
```

Вывод: изменения в `/etc`, `/tmp`, `/var`, `/dev`, `/media` не нужно считать постоянными без отдельной проверки механизма сохранения во flash.

## Что остаётся проверить

- Точное назначение сервиса `TCP/7060`.
- Механизм постоянного сохранения настроек во flash.
- Назначение `SDA`/`CLK`.
- Есть ли полноценный USB data-интерфейс.
- Полный дамп SPI flash.
