# Monitor И Wi-Fi

Короткая сводка по monitor mode и текущей рабочей архитектуре.

## Текущая Схема

Рабочий вариант:

```text
MT7628 встроенный Wi-Fi
  ra1 = AP/control network

TP-Link WN723N / RTL8188EUS
  wlan0 = monitor/capture interface
```

Одно radio держит управление устройством, второе radio занимается capture. Это правильная архитектура для этого проекта.

Проверено на прошитом образе:

```text
8188eu loaded
mt_wifi loaded
ra1 ESSID:"AT" IP 192.168.10.123 channel 11
wlan0 Mode:Monitor frequency 2.462 GHz
/sys/class/net/wlan0/type = 803
```

Management AP:

```text
SSID: AT
Authentication: WPA2-Personal
Cipher: CCMP
Password: 12345678
BSSID: e8:ab:fa:ae:6e:a1
Channel: 11
```

## Что Выяснено Про MT7628

`mt_wifi.ko` поддерживает AP/STA, но полноценный постоянный Linux monitor на встроенном radio не подтвержден.

Факты:

```text
ra1 = рабочий AP/control interface
ra0 = неактивный STA-like interface, MAC 00:00:00:00:00:00
```

Не использовать:

```text
ifconfig ra0 up
iwconfig ra0 mode monitor
iwpriv ra0 set MonitorMode=1/2
```

Почему: `ra0` не стал monitor-интерфейсом, а попытки поднять его могут положить Wi-Fi.

`ra1 promisc`:

```text
работает
AP остается живым
это НЕ 802.11 monitor mode
```

`ATE RXFRAME`:

```text
iwpriv ra1 set ATE=ATESTART
iwpriv ra1 set ATECHANNEL=11
iwpriv ra1 set ATE=RXFRAME
iwpriv ra1 set ATE=ATESTOP
```

Это заводской radio RX test. Он disruptive: деавторизует клиентов и может требовать reconnect/reboot. Запускать только через UART.

## WN723N / RTL8188EUS

USB hardware path подтвержден:

```text
adapter: TP-Link WN723N
chip: RTL8188EUS
USB ID: 0bda:8179
USB host: OK
speed: 480M
```

Проблема драйвера была не в пайке и не в USB, а в совместимости Realtek driver probe path с vendor kernel MT7628 Linux 2.6.36.

Ключевые этапы:

- `NO-PROBE` вариант грузился без падения, но не цеплял устройство.
- Ранние probe-варианты падали в kernel Oops.
- После ABI-патчей текущий `8188eu` грузится, цепляет WN723N и поднимает `wlan0`.

Сохраненный рабочий драйвер:

```text
artifacts\drivers\rtl8188eus\8188eu_vendorabi_pm_skb_slim.ko
artifacts\drivers\rtl8188eus\8188eu_vendorabi_pm_skb_slim.ko.lzma
```

## Capture / Airtools

Текущая прошивка запускает airtools supervisor и airodump collector. Детали API и storage описаны в [AIRTOOLS.md](AIRTOOLS.md).

Runtime storage:

```text
/tmp/airhs
```

Важно: `/tmp` RAM-backed, handshakes не переживают power loss.

## Правила

- Не возвращаться к `ra0 monitor` как к рабочему пути.
- `ATE RXFRAME` запускать только через UART.
- Для постоянной системы использовать `ra1` как AP, `wlan0` как monitor.
- Не писать `mtd1/mtd2/mtd3` ради monitor-задач.
- Изменения monitor payload делать только через новый `mtd4` image и правила из [BRICK.md](BRICK.md).

## Что Осталось

- Проверить реальный WPA handshake capture.
- Проверить replacement logic: один BSSID хранит последний handshake.
- Решить persistence для режима capture и/или handshakes.
- Привести RTL8188EUS build chain к воспроизводимому clean rebuild.
