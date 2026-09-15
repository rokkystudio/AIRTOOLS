# ENDOSCOPE

Исследование старой платы Wi-Fi эндоскопа на базе Linux с целью получить полный доступ к системе, сохранить оригинальную прошивку и определить варианты повторного использования платы.

## Плата

Маркировка PCB:

- `ML-7066`
- `REV:3.0`
- дата на шелкографии: `2018-10-18`

Фотографии платы:

- `1789487224941.jpg`
- `1789487224948.jpg`
- `1789489367549.jpg`

Каталог проекта:

`D:\PROJECTS\ENDOSCOPE`

## Подтверждённая аппаратная платформа

Загрузочный лог UART подтвердил:

- SoC: MediaTek/Ralink `MT7628`
- U-Boot: `U-Boot 1.1.3`
- Ralink U-Boot: `5.0.0.0`
- build U-Boot: `Aug 9 2018 17:34:36`
- ASIC: `7628_MP`
- CPU frequency: `580 MHz`
- RAM: `64 MB DDR`
- SPI flash: `Winbond W25Q32BV`
- JEDEC manufacturer/device: `EF 40 16`
- flash size: `4 MiB`

U-Boot сообщает:

```text
Board: Ralink APSoC DRAM: 64 MB
flash manufacture id: ef, device id 40 16
find flash: W25Q32BV
Ralink UBoot Version: 5.0.0.0
ASIC 7628_MP
Flash component: SPI Flash
The CPU freq = 580 MHZ
```

## Linux

Прошивка запускает MIPS Linux:

```text
Linux version 2.6.36 (tony@ubuntu) (gcc version 4.6.3 (Buildroot 2012.11.1)) #772 Mon Mar 11 17:01:13 CST 2019
```

CPU:

```text
system type : MT7628
cpu model   : MIPS 24Kc V5.5
BogoMIPS    : 386.04
ASEs        : mips16 dsp
```

BusyBox:

```text
BusyBox v1.23.0 (2018-03-30 18:02:20 CST)
```

Не все стандартные BusyBox applets включены. В частности, отдельные `id`, `uname` и `df` отсутствуют, и встроенный `/bin/busybox` также не содержит этих applets.

## UART

UART полностью подтверждён.

Площадки платы:

- `T` — TX платы
- `R` — RX платы
- `GND` — земля

Подключение CP2102:

```text
Плата             CP2102

GND  ------------ GND
T    ------------ RXD
R    ------------ TXD
```

Питание CP2102 к плате не подключается:

```text
CP2102 5V   -> НЕ ПОДКЛЮЧАТЬ
CP2102 3V3  -> НЕ ПОДКЛЮЧАТЬ
```

Подтверждённые параметры UART:

```text
57600 baud
8 data bits
No parity
1 stop bit
Flow control: None
```

На SMART_TV CP2102 определяется как:

```text
Silicon Labs CP210x USB to UART Bridge (COM3)
VID_10C4&PID_EA60
```

UART Linux использует:

```text
/dev/ttyS1
```

После загрузки init запускает shell напрямую:

```text
starting pid 249, tty '/dev/ttyS1': '/bin/sh'

BusyBox v1.23.0 (2018-03-30 18:02:20 CST) built-in shell (ash)
Enter 'help' for a list of built-in commands.

#
```

Аутентификация на UART отсутствует.

Проверка `/proc/self/status` из этого shell показывает:

```text
Uid: 0 0 0 0
Gid: 0 0 0 0
CapPrm: ffffffffffffffff
CapEff: ffffffffffffffff
```

То есть UART предоставляет полноценные права UID 0.

В выводе `ps` пользователь отображается как `molink`, потому что в `/etc/passwd` UID 0 назначен имени `molink`.

Сохранённые захваты UART:

- `uart_57600_capture.bin`
- `uart_57600_capture.txt`

## Учётная запись Linux

На устройстве:

```text
molink:GGyh/PXa6D1n6:0:0:Adminstrator:/:/bin/sh
```

То есть:

- login: `molink`
- UID: `0`
- GID: `0`
- shell: `/bin/sh`
- password hash хранится непосредственно в `/etc/passwd`
- формат хеша выглядит как старый DES crypt

Исходный пароль пока не определён.

## Разметка SPI flash

`/proc/mtd`:

```text
dev:    size     erasesize  name
mtd0: 00400000 00010000 "ALL"
mtd1: 00030000 00010000 "Bootloader"
mtd2: 00010000 00010000 "Config"
mtd3: 00010000 00010000 "Factory"
mtd4: 003b0000 00010000 "Kernel"
```

Разметка:

- `mtd0` ALL — `0x400000` = 4 MiB
- `mtd1` Bootloader — `0x30000` = 192 KiB
- `mtd2` Config — `0x10000` = 64 KiB
- `mtd3` Factory — `0x10000` = 64 KiB
- `mtd4` Kernel — `0x3B0000`

Перед любыми экспериментами необходимо сохранить полный `mtd0`.

## Kernel image

U-Boot загружает образ из:

```text
bc050000
```

Заголовок:

```text
Image Name:   Linux Kernel Image
Image Type:   MIPS Linux Kernel Image (lzma compressed)
Data Size:    3018696 Bytes
Load Address: 80000000
Entry Point:  8000c150
```

## Filesystems

Текущие mount points:

```text
rootfs on / type rootfs (rw)
proc on /proc type proc (rw,relatime)
none on /var type ramfs (rw,relatime)
none on /dev type ramfs (rw,relatime)
none on /etc type ramfs (rw,relatime)
none on /tmp type ramfs (rw,relatime)
none on /media type ramfs (rw,relatime)
none on /sys type sysfs (rw,relatime)
none on /proc/bus/usb type usbfs (rw,relatime)
devpts on /dev/pts type devpts (rw,relatime,mode=600)
```

`/etc`, `/tmp`, `/var` и несколько других каталогов работают из RAM.

## Процессы

Основные пользовательские процессы:

```text
init
nvram_daemon
app_detect
app_cam
udhcpd /etc_ro/udhcpd.conf
/bin/sh
telnetd
```

Приложение камеры называется `app_cam`.

Конфигурация DHCP:

```text
/etc_ro/udhcpd.conf
```

## Wi-Fi

Wi-Fi точка доступа платы:

- SSID: `ENDOSCOPE`
- сеть открытая, без шифрования
- BSSID / MAC: `E8:AB:FA:AE:6E:A1`
- канал: 11

После подключения SMART_TV:

- SMART_TV: `192.168.10.36/24`
- эндоскоп / gateway: `192.168.10.123`
- DNS: `168.95.1.1`, `8.8.8.8`

На Linux интерфейс камеры:

```text
ra1
MAC E8:AB:FA:AE:6E:A1
IP 192.168.10.123
Mask 255.255.255.0
```

Также присутствуют:

- `ra0`
- `eth2`
- `lo`

## Сетевые сервисы

На `192.168.10.123` подтверждены:

- TCP/23 — Telnet
- TCP/7060 — сервис камеры / видеопотока

TCP/22:

- закрыт
- SSH daemon сейчас не запущен

Попытка подключения:

```text
ssh 192.168.10.123

ssh: connect to host 192.168.10.123 port 22: Connection refused
```

Telnet отвечает:

```text
MoLink login:
```

## Найденный похожий разбор

Nathan Henrie исследовал очень похожий Wi-Fi эндоскоп.

Part 1:

https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-1/

Part 2:

https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-2/

Совпадения с нашим устройством:

- `192.168.10.123`
- Telnet на TCP/23
- сервис на TCP/7060
- Ralink/MediaTek Linux
- Winbond W25Q32
- UART 57600
- сходная архитектура firmware

В статье автор нашёл:

```text
login: tony
password: tony4321
```

На нашем экземпляре эти credentials через Telnet не сработали.

При этом в строке сборки нашего ядра присутствует:

```text
tony@ubuntu
```

Это имя пользователя build-машины и не означает, что `tony` является login устройства.

## USB-разъём эндоскопа

При подключении штатного USB платы к Windows новое PnP-устройство не появляется.

Baseline:

- до подключения: 168 PnP-устройств
- после подключения: 168
- Added: 0
- Removed: 0
- Changed: 0

Поэтому штатный USB-разъём, вероятно, используется только для питания/зарядки.

На обратной стороне возле USB находится микросхема семейства TP, похожая по назначению на зарядный контроллер TP4056. Точную маркировку корпуса необходимо подтвердить отдельно.

## Остальные сервисные площадки

На PCB подписаны:

```text
GND

TXN
TXP
RXN
RXP

R
T

SDA
CLK
```

### TXN / TXP / RXN / RXP

Это дифференциальные пары и не UART.

Не подключать их к CP2102.

### SDA / CLK

Отдельный синхронный интерфейс, вероятно I2C.

К UART не относится.

## Следующие задачи

1. Сохранить полный дамп `/dev/mtd0` на SMART_TV без записи во flash.
2. Посчитать SHA-256 дампа.
3. Сохранить отдельно Bootloader, Config, Factory и Kernel.
4. Исследовать содержимое firmware офлайн.
5. Найти конфигурацию Telnet и источник password hash.
6. Исследовать `app_cam` и протокол TCP/7060.
7. Проверить U-Boot prompt и доступные команды.
8. Разобраться с возможностью SSH.
9. Сохранить важные NVRAM/Factory данные перед любыми изменениями.
10. После полного backup определить варианты повторного использования платы.

## Важные ограничения

До создания полного backup:

- не стирать SPI flash;
- не записывать в MTD;
- не запускать firmware update;
- не менять Factory/Config;
- не подавать 5 V на UART;
- не соединять питание CP2102 с питанием платы;
- не подключать CP2102 к `TXN/TXP/RXN/RXP`.

## Восстановление Telnet-пароля

Дата: 2026-09-15

Цель: получить штатный логин/пароль для Telnet-доступа по Wi-Fi, чтобы работать с устройством без UART.

### Исходные данные

Через UART shell был прочитан `/etc/passwd`.

Актуальная строка пользователя:

```text
molink:GGyh/PXa6D1n6:0:0:Adminstrator:/:/bin/sh
```

Расшифровка:

```text
login: molink
hash:  GGyh/PXa6D1n6
UID:   0
GID:   0
home:  /
shell: /bin/sh
```

`GGyh/PXa6D1n6` — не plaintext-пароль, а classic Unix DES crypt hash.

### Подготовка hashcat

Hash был сохранён в файл:

```powershell
Set-Content -NoNewline -Encoding ASCII D:\PROJECTS\ENDOSCOPE\hash.txt 'GGyh/PXa6D1n6'
```

Используемый режим hashcat:

```text
-m 1500
descrypt, DES (Unix), Traditional DES
```

Алфавит перебора:

```text
a-z0-9
```

В hashcat:

```text
?l = маленькие английские буквы a-z
?d = цифры 0-9
-1 '?l?d'
```

Classic DES crypt учитывает только первые 8 символов пароля, поэтому максимальная полезная длина перебора — 8.

### Перебор длины 1..6

Команда:

```powershell
.\hashcat.exe -m 1500 -a 3 D:\PROJECTS\ENDOSCOPE\hash.txt -1 '?l?d' --increment --increment-min 1 --increment-max 6 '?1?1?1?1?1?1' --session endoscope_molink_len1_6 --potfile-path D:\PROJECTS\ENDOSCOPE\hashcat-endoscope.potfile --outfile D:\PROJECTS\ENDOSCOPE\hashcat-found.txt --outfile-format 2 --status --status-timer 10 -w 3 -O
```

Результат:

```text
Status: Exhausted
Recovered: 0/1
```

Пароль длиной 1..6 не найден.

### Перебор длины 8

Команда:

```powershell
.\hashcat.exe -m 1500 -a 3 D:\PROJECTS\ENDOSCOPE\hash.txt -1 '?l?d' '?1?1?1?1?1?1?1?1' --session endoscope_molink_len8 --potfile-path D:\PROJECTS\ENDOSCOPE\hashcat-endoscope.potfile --outfile D:\PROJECTS\ENDOSCOPE\hashcat-found.txt --outfile-format 2 --status --status-timer 10 -w 3
```

Результат:

```text
Session: endoscope_molink_len8
Status: Cracked
Recovered: 1/1
Progress: 624843292672/2821109907456
Speed: ~1274.3 MH/s
GPU: NVIDIA GeForce RTX 3060 Ti
```

Проверка результата:

```powershell
.\hashcat.exe -m 1500 D:\PROJECTS\ENDOSCOPE\hash.txt --potfile-path D:\PROJECTS\ENDOSCOPE\hashcat-endoscope.potfile --show
```

Вывод:

```text
GGyh/PXa6D1n6:molinkad
```

### Найденные данные доступа

```text
Telnet host: 192.168.10.123
Telnet port: 23
login: molink
password: molinkad
```

Проверка через PuTTY:

```powershell
& "C:\Program Files\PuTTY\putty.exe" -telnet 192.168.10.123 23
```

При запросе логина:

```text
MoLink login: molink
Password: molinkad
```

