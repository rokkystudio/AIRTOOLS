# ENDOSCOPE: получение доступа к терминалу

Проект описывает, как был получен доступ к терминалу старого Wi-Fi эндоскопа. Основная история: сначала нашли UART и получили shell напрямую, затем через UART получили данные для восстановления штатного Telnet-доступа по Wi-Fi.

Рабочая папка проекта:

```text
D:\PROJECTS\ENDOSCOPE
```

## Краткий итог

- Устройство поднимает Wi-Fi AP `ENDOSCOPE`.
- IP устройства в этой сети: `192.168.10.123`.
- На устройстве открыт Telnet `TCP/23`.
- Через UART получен shell без Telnet-входа.
- Через UART был прочитан локальный файл учётных записей устройства.
- Доступ по Telnet восстановлен через hashcat.
- Логины, пароли, hash-значения и строки учётных записей вынесены в отдельный файл `CREDENTIALS.md`.
- Активные BAT-файлы подключения лежат в `scripts\`.

## Быстрое подключение

### Wi-Fi / Telnet

Сначала подключить компьютер к Wi-Fi сети устройства `ENDOSCOPE`, затем запустить:

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-wifi.bat
```

Данные входа лежат отдельно:

```text
D:\PROJECTS\ENDOSCOPE\CREDENTIALS.md
```

### UART напрямую

Запустить:

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat
```

Для другого COM-порта:

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat COM4
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

## Что реально получено на нашем устройстве

Этот раздел содержит только то, что было получено на нашем экземпляре через фото, UART, Windows/USB/Wi-Fi проверки и локальное восстановление доступа.

### Фото и маркировка платы

Фотографии лежат в:

```text
images\
```

На плате прочитано:

```text
ML-7066 REV:3.0
2018-10-18
```

Test pads:

```text
GND          земля
R / T        UART RX/TX
TXN/TXP      дифференциальная пара, не UART
RXN/RXP      дифференциальная пара, не UART
SDA/CLK      назначение требует отдельной проверки
```

### Проверка USB

USB-подключение самого эндоскопа к Windows не дало нового PnP-устройства. По результату этой проверки USB не рассматривается как подтверждённый data-интерфейс.

CP2102 USB-UART определился отдельно как:

```text
Silicon Labs CP210x USB to UART Bridge (COM3)
VID_10C4&PID_EA60
```

### Wi-Fi и сеть

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

### UART boot log

Основной boot log:

```text
logs\uart-20260915-200900-57600.txt
logs\uart-20260915-200900-57600.bin
```

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

### Linux и flash layout

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

Разметка flash из `/proc/mtd`:

| dev  | size     | erasesize | name       |
|------|----------|-----------|------------|
| mtd0 | 00400000 | 00010000  | ALL        |
| mtd1 | 00030000 | 00010000  | Bootloader |
| mtd2 | 00010000 | 00010000  | Config     |
| mtd3 | 00010000 | 00010000  | Factory    |
| mtd4 | 003b0000 | 00010000  | Kernel     |

SPI flash:

```text
model: W25Q32BV
size: 4 MiB
```

Mount layout важен: `/etc`, `/tmp`, `/var`, `/dev`, `/media` находятся в RAM/ramfs. Поэтому изменения в `/etc` не нужно считать постоянными без отдельной проверки механизма сохранения во flash.

## Как восстанавливали доступ по Telnet

Через UART shell был прочитан локальный файл учётных записей. На нашем устройстве отдельные shadow-файлы не найдены, поэтому hash находился прямо в файле учётных записей.

Секретные значения вынесены в:

```text
CREDENTIALS.md
```

Использовался hashcat:

```text
hashcat 6.2.6
mode: 1500, descrypt / Traditional DES
GPU: NVIDIA GeForce RTX 3060 Ti
charset: a-z0-9
```

Сначала был перебран диапазон длины `1..6`:

```text
Status: Exhausted
Recovered: 0/1
```

Затем значение было найдено на длине `8`:

```text
Session: endoscope_molink_len8
Status: Cracked
Recovered: 1/1
Speed: about 1274 MH/s
Progress at crack: about 22.15% of full length-8 keyspace
```

Файлы hashcat:

```text
hashcat\hash.txt
hashcat\hashcat-endoscope.potfile
hashcat\hashcat-found.txt
hashcat\run-len1-6.bat
hashcat\run-len7.bat
hashcat\run-len8.bat
hashcat\show-result.bat
```

## Внешняя статья о похожем устройстве

Отдельно от наших результатов использовалась статья Nathan Henrie о похожем Wi-Fi эндоскопе:

```text
https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-1/
https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-2/
```

Из статьи были взяты только ориентиры для проверки:

- похожий адрес устройства `192.168.10.123`;
- наличие Telnet на `23/tcp`;
- наличие сервиса на `7060/tcp`;
- похожий MoLink banner;
- похожая SPI flash Winbond W25Q32;
- UART `57600`;
- пример чужих данных входа из статьи.

Важно: данные из статьи не считаются результатом нашего устройства, пока не подтверждены нашими фото, UART-логами или сетевыми проверками. Чужие данные входа из статьи на нашем устройстве не подошли и не используются.

## Что остаётся гипотезой

- Точное назначение сервиса `TCP/7060` пока не разобрано.
- Механизм постоянного сохранения настроек во flash пока не проверен.
- Назначение `SDA`/`CLK` требует отдельной проверки.
- Полноценный USB data-интерфейс на плате не подтверждён.
- Перед любыми постоянными изменениями нужен полный дамп SPI flash.

## Структура проекта

```text
README.md                  описание проекта без логинов, паролей и hash-значений
CREDENTIALS.md             логины, пароли, hash-значения и строки учётных записей
images\                    фотографии платы
logs\                      UART boot logs и shell output
hashcat\                   hashcat input, potfile, найденный пароль и BAT-файлы
scripts\                   BAT-файлы подключения
docs\                      служебные инструкции и задания для чистки README
dumps\                     дампы flash/firmware, если появятся
tools\                     локальные утилиты, например portable PuTTY
_backup\                   backup перед реорганизацией и правками
```

Активные BAT-файлы подключения:

```text
scripts\connect-endoscope-wifi.bat
scripts\connect-endoscope-uart.bat
```

## Следующие шаги

1. Проверить штатный Telnet по Wi-Fi через `scripts\connect-endoscope-wifi.bat`.
2. Сделать полный backup SPI flash до любых постоянных изменений.
3. Разобрать сервис `TCP/7060`.
4. Не писать во flash до появления проверенного полного дампа.
