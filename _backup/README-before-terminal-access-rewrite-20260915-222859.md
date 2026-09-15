# ENDOSCOPE reverse engineering notes

Исследование платы Wi-Fi эндоскопа на базе Linux: доступ к системе, сохранение исходной прошивки и оценка вариантов повторного использования платы.

## Как читать этот README

Данные разделены по происхождению:
- **Проверено на нашем устройстве** — подтверждается файлами и логами проекта.
- **Данные из внешней статьи** — относятся к похожему устройству Nathan Henrie.
- **Гипотезы / требует проверки** — старые наблюдения и выводы без достаточного локального подтверждения.

Не переносить сведения из статьи в локальные факты только из-за совпадения платформы или адресов.

## Быстрый доступ

Корень: `D:\PROJECTS\ENDOSCOPE`

UART:
- helper: `scripts\connect-endoscope-uart.bat`
- параметры: `57600 8N1`, flow control `None`
- shell: `/dev/ttyS1`

Wi-Fi / Telnet:
- локально подтверждённый IP `ra1`: `192.168.10.123`
- `telnetd` присутствует среди процессов
- helper: `scripts\connect-endoscope-wifi.bat`
- login: `molink`
- пароль: `PASSWORD`
- хеш: `HASH`

## Проверено на нашем устройстве

Основные локальные источники:
- `logs\uart-20260915-200900-57600.txt`
- `logs\uart-shell-20260915-201108.txt`
- `logs\uart-readonly-20260915-201154.txt`
- `logs\accounts-sanitized-20260915-201543.txt`
- `hashcat\`, `images\`, `scripts\`

### Плата и загрузка

По фотографиям и рабочим заметкам проекта:
- PCB: `ML-7066`
- revision: `REV:3.0`
- дата на шелкографии: `2018-10-18`

Фотографии находятся в `images\`.

UART boot log подтверждает:
- SoC/platform: MediaTek/Ralink `MT7628`, ASIC `7628_MP`
- U-Boot `1.1.3`, Ralink U-Boot `5.0.0.0`
- build U-Boot: `Aug 9 2018 17:34:36`
- CPU: `580 MHz`
- RAM: `64 MB DDR`
- SPI flash: `Winbond W25Q32BV`, JEDEC `EF 40 16`, размер `4 MiB`
- kernel image: flash `0xbc050000`, size `3018696` bytes, load `0x80000000`, entry `0x8000c150`, LZMA

### Linux и UART shell

Локальные логи подтверждают:
- Linux `2.6.36`
- CPU model: `MIPS 24Kc V5.5`
- BusyBox `1.23.0`
- kernel build string содержит `tony@ubuntu`
- `/etc_ro/inittab`: `ttyS1::respawn:/bin/sh`
- UART даёт shell без отдельного login prompt
- `/etc/passwd`: пользователь `molink`, `UID 0`, `GID 0`, home `/`, shell `/bin/sh`
- `/etc/shadow` отсутствует
- команды `id`, `uname` и `df` отсутствуют

`tony@ubuntu` — build-пользователь ядра, а не подтверждение login `tony`.

### Flash layout

Разметка из `/proc/mtd`:

| MTD    |       Size | Name         |
|--------|-----------:|--------------|
| `mtd0` | `0x400000` | `ALL`        |
| `mtd1` | `0x030000` | `Bootloader` |
| `mtd2` | `0x010000` | `Config`     |
| `mtd3` | `0x010000` | `Factory`    |
| `mtd4` | `0x3B0000` | `Kernel`     |

До полного backup не записывать во flash и не менять `Factory`/`Config`.

### Сеть и процессы

`ifconfig -a` подтверждает для `ra1`:
- MAC: `E8:AB:FA:AE:6E:A1`
- IP: `192.168.10.123`
- mask: `255.255.255.0`

`/etc_ro/udhcpd.conf` содержит:
- DHCP range: `192.168.10.20` .. `192.168.10.100`
- router: `192.168.10.123`
- DNS: `168.95.1.1`, `8.8.8.8`

Среди процессов подтверждены `nvram_daemon`, `app_detect`, `app_cam`, `udhcpd`, `telnetd` и `/bin/sh`.

Сохранённый `RT2860AP.dat` содержит `SSID1=MT7628_AP`, `AuthMode=OPEN`, `EncrypType=NONE`.
Это содержимое конфигурационного файла, а не доказательство фактически транслируемого SSID.

### Восстановление доступа

Локально полученный `/etc/passwd` содержит DES crypt hash пользователя `molink`.

Материалы находятся в `hashcat\`:
- hashcat mode: `-m 1500` (`descrypt`)
- mask charset: `a-z0-9`
- перебор `1..6` результата не дал
- отдельный перебор длины `8` дал plaintext result
- результат: `hashcat\hashcat-found.txt`
- potfile: `hashcat\hashcat-endoscope.potfile`

Данные доступа нашего экземпляра:
- login: `molink`
- пароль: `PASSWORD`
- хеш: `HASH`

Для подключения используется `scripts\connect-endoscope-wifi.bat`.

## Данные из внешней статьи о похожем устройстве

Источник: Nathan Henrie:
- https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-1/
- https://n8henrie.com/2019/02/reverse-engineering-my-wifi-endoscope-part-2/

Статья описывает другой экземпляр устройства. В старых заметках проекта со статьёй связывались:
- `192.168.10.123`
- Telnet на TCP/23
- сервис на TCP/7060
- Ralink/MediaTek Linux
- Winbond W25Q32
- UART `57600`
- похожая структура firmware
- данные доступа из статьи: login `tony`, password `tony4321`

На нашем устройстве независимо подтверждены локальными логами только часть совпадений: MT7628/Ralink, W25Q32BV, UART `57600`, IP `192.168.10.123` и наличие процесса `telnetd`.

Данные доступа `tony` / `tony4321` относятся только к статье и не являются данными доступа нашего экземпляра.

## Гипотезы / требует проверки

- **TCP/7060 открыт и обслуживается `app_cam`.** Повторно проверить порт и сохранить результат в `logs\`.
- **TCP/23 доступен по сети и показывает `MoLink login:`.** Сохранить Telnet capture с banner и результатом аутентификации.
- **TCP/22 закрыт.** Повторить проверку и сохранить результат.
- **Фактический SSID — `ENDOSCOPE`.** Сохранить Wi-Fi scan; текущий `RT2860AP.dat` содержит `SSID1=MT7628_AP`.
- **Штатный USB-разъём только для питания/зарядки.** Повторить PnP comparison и сохранить лог.
- **Микросхема возле USB относится к TP4056.** Подтвердить маркировку по макрофото.
- **`SDA` / `CLK` — I2C.** Проверить трассировку или сигнал логическим анализатором.
- **Назначение `TXN/TXP/RXN/RXP`.** Определить по трассировке и измерениям.
- **Способ сохранения настроек в Config/NVRAM.** Исследовать после полного backup.
- **Структура firmware совпадает со статьёй.** Проверять только по собственному dump.

## Структура проекта

- `images\` — фотографии платы.
- `logs\` — UART captures и вывод команд.
- `hashcat\` — hash, potfile, результат и BAT-файлы.
- `scripts\` — helper scripts для UART и Telnet.
- `docs\` — служебная документация.
- `dumps\` — будущие дампы flash/firmware.
- `tools\` — вспомогательные инструменты.
- `_backup\` — резервные копии перед правками.

## Следующие шаги

1. Сохранить полный `/dev/mtd0` без записи во flash.
2. Посчитать SHA-256 полного dump.
3. Сохранить отдельно Bootloader, Config, Factory и Kernel.
4. Повторно проверить TCP/23, TCP/22 и TCP/7060 с сохранением результатов.
5. Сохранить фактический Wi-Fi scan с SSID/BSSID.
6. Исследовать `app_cam` и сетевой протокол.
7. Разобрать firmware офлайн после полного backup.
8. Не запускать firmware update и не изменять MTD до проверенного backup.
