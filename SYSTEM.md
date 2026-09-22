# AIRTOOLS: общая информация о системе

## Устройство

Wi-Fi эндоскоп построен на платформе MediaTek/Ralink MT7628.

Основные параметры:

| Параметр     | Значение                |
|--------------|-------------------------|
| SoC          | MediaTek/Ralink MT7628  |
| CPU          | MIPS 24Kc               |
| Architecture | MIPS32 little-endian    |
| RAM          | около 64 MiB            |
| SPI flash    | Winbond W25Q32BV, 4 MiB |
| UART         | ttyS1, 57600 8N1        |

## Прошивка

| Компонент    | Версия                          |
|--------------|---------------------------------|
| Firmware     | NuCam-7688-3003                 |
| Build        | 2019-03-11 17:00:46             |
| Linux kernel | 2.6.36                          |
| BusyBox      | 1.23.0                          |
| libc         | uClibc 0.9.33.2                 |
| Toolchain    | GCC 4.6.3 / Buildroot 2012.11.1 |

Система представляет собой минимальную embedded Linux-прошивку без обычного пакетного менеджера.

Root filesystem встроен непосредственно в kernel image как LZMA-compressed initramfs.

## Flash layout

Полный SPI flash имеет размер 4 MiB.

| MTD  |     Offset |       Size | Назначение                           |
|------|-----------:|-----------:|--------------------------------------|
| mtd1 | `0x000000` | `0x030000` | U-Boot + служебные данные приложения |
| mtd2 | `0x030000` | `0x010000` | Ralink NVRAM / Config                |
| mtd3 | `0x040000` | `0x010000` | Factory / MT7628 EEPROM              |
| mtd4 | `0x050000` | `0x3B0000` | Linux kernel + встроенный rootfs     |

### mtd1

Основная часть содержит U-Boot.

В последнем 64 KiB sector также находятся persistent параметры приложения камеры. Поэтому название MTD-раздела `Bootloader` не означает, что весь диапазон используется только U-Boot.

### mtd2

Содержит стандартные Ralink NVRAM banks:

| Bank    | Offset внутри mtd2 |     Size |
|---------|-------------------:|---------:|
| `2860`  |           `0x2000` | `0x4000` |
| `rtdev` |           `0x6000` | `0x2000` |
| `cert`  |           `0x8000` | `0x2000` |
| `wapi`  |           `0xA000` | `0x5000` |

В них находятся параметры Wi-Fi, LAN/WAN, DHCP, security, WPS, driver settings и другие настройки Ralink SDK.

### mtd3

Содержит MT7628 EEPROM / factory calibration data.

Здесь же хранится индивидуальный MAC address устройства.

### mtd4

Содержит U-Boot uImage с Linux kernel и встроенным initramfs.

## Root filesystem

Основные каталоги:

```text
/bin
/sbin
/lib
/usr
/etc_ro
/etc
/dev
/proc
/sys
/tmp
/var
/media
/mnt
```

`/etc_ro` содержит постоянные шаблоны и boot scripts.

`/etc`, `/var`, `/tmp` и часть других runtime-каталогов создаются в RAM.

## Boot

Главный init script:

```text
/etc_ro/rcS
```

Во время загрузки примерно выполняется:

1. инициализация файловых систем;
2. запуск NVRAM daemon;
3. настройка устройств через mdev;
4. загрузка Wi-Fi configuration;
5. запуск supervisor приложения камеры;
6. запуск Wi-Fi AP;
7. загрузка GPIO/PWM modules;
8. загрузка UVC/V4L2 modules;
9. запуск Telnet.

UART `ttyS1` запускает прямой shell и является удобным recovery/debug каналом.

## Основные приложения

### app_cam

Главное приложение камеры.

Отвечает за:

- работу с USB UVC камерой;
- V4L2 capture;
- MJPEG/YUYV video;
- сетевую передачу video;
- управление параметрами камеры;
- Wi-Fi-related команды;
- PWM;
- persistent application settings;
- firmware update.

### app_detect

Supervisor/watchdog для `app_cam`.

Следит за процессом камеры и перезапускает его при необходимости.

### app_host

USB host application на базе libusb/usbmuxd-подобной логики.

В штатной boot sequence не запускается.

### app_mkfs

Используется для работы со съёмным storage.

## Kernel modules

### Wi-Fi

```text
mt_wifi.ko
```

MediaTek/Ralink Wi-Fi driver.

### Video

Используются стандартные V4L2/UVC modules:

```text
videodev.ko
v4l2-common.ko
v4l1-compat.ko
v4l2-int-device.ko
uvcvideo.ko
```

### GPIO / PWM

```text
gpio_drv.ko
pwm_drv.ko
```

## Основные библиотеки

Прошивка использует:

- uClibc 0.9.33.2;
- libpthread;
- libm;
- libdl;
- librt;
- libusb;
- zlib;
- PCRE;
- Ralink libnvram.

## Сеть

Основной Wi-Fi режим — Access Point.

Устройство также поддерживает STA/client mode.

Из известных сервисов:

| Protocol |  Port | Назначение                     |
|----------|------:|--------------------------------|
| TCP      |    23 | Telnet                         |
| TCP      |  7060 | video stream                   |
| TCP      |  8060 | app_cam command/update service |
| TCP      |  9060 | TCP ↔ UART bridge              |
| UDP      | 50000 | app_cam command service        |
| UDP      | 52100 | UDP ↔ UART bridge              |

## Video stream

TCP/7060 передаёт собственный framed video stream.

Кадры имеют общий вид:

```text
BoundaryS
metadata
video payload
BoundaryE
```

Приложение поддерживает V4L2 formats:

```text
MJPG
YUYV
```

В сохранённой конфигурации нашего устройства установлен MJPG и разрешение 1280x720.

## Управление

`app_cam` поддерживает команды для:

- настройки Wi-Fi имени и пароля;
- изменения Wi-Fi channel;
- управления PWM;
- чтения и изменения camera controls;
- изменения resolution;
- reboot;
- firmware update.

Firmware update записывает новый image в `mtd4`.

Поэтому неизвестные команды control service лучше не отправлять на работающем устройстве без UART recovery.

## Persistent configuration

Используются три основных области:

1. application parameters в конце `mtd1`;
2. Ralink NVRAM в `mtd2`;
3. Factory/EEPROM data в `mtd3`.

Для обычного исследования достаточно сохранять полный flash dump перед экспериментами.

## Полезные системные утилиты

В прошивке присутствуют:

```text
busybox
flash
ralink_init
nvram_get
nvram_set
mtd_write
iwconfig
iwlist
iwpriv
iperf
lsusb
gpio
switch
mii_mgr
```

`flash`, `nvram_set` и `mtd_write` способны изменять persistent flash и требуют осторожности.

## Основные исходные материалы проекта

Сохранённые flash dumps находятся в:

```text
dumps/
```

Более общая информация об устройстве находится в:

- [DEVICE.md](DEVICE.md)
- [FIRMWARE.md](FIRMWARE.md)
- [README.md](README.md)

## Модифицированные образы

Разделы выше описывают возможности и состав заводской прошивки.

Ранняя modified-сборка `dumps\modified\mtd4_connectivity.bin` была предназначена для режима Wi-Fi AP без эндоскопа и удаляла из rootfs:

- `app_cam`;
- старый `app_detect`;
- `video_ko.sh`;
- UVC/V4L2 video modules.

Вместо них был добавлен небольшой `/bin/endoscope-connectivity`, который обслуживает локальные DNS/HTTP connectivity checks телефона.

DHCP в этой ветке брал LAN/DHCP параметры из Ralink NVRAM и выдавал IP самого AP как DNS.

Актуальный прошитый образ проекта описан в [DEVICE.md](DEVICE.md) и [FIRMWARE.md](FIRMWARE.md):

```text
dumps\verified\mtd4_airtools_tcp_scan_20260922.bin
```

Он добавляет WN723N/RTL8188EUS monitor, airtools TCP API и WPA2 management AP `AT`.

Правила сборки, RAM test boot и recovery находятся в [FIRMWARE.md](FIRMWARE.md).
