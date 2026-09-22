# AIRTOOLS Платформа

Этот файл фиксирует актуальную платформу управления поверх прошивки `mtd4`: AP `AT`, WN723N monitor, UDP API и хранение handshakes.

## Firmware Baseline

```text
dumps\verified\mtd4_at_wpa2_airtools_wn723n_20260920.bin
size=3866624
sha256=7443772442fbbc038305f75659d8b628b319b1da73f99f699a43904f8271124d
```

Management AP:

```text
SSID: AT
auth: WPA2PSK
cipher: AES/CCMP
password: 12345678
IP: 192.168.10.123
channel: 11
```

## Runtime Components

```text
/bin/airtools       14424
/bin/airwifi         1231
/bin/airodump       13272
/bin/aireplay        6604
/bin/wn723n-monitor  2157
/bin/wn723n-extract 14360
```

Kernel/modules:

```text
mt_wifi loaded
8188eu loaded
ra1 = AP/control interface
wlan0 = monitor interface
/sys/class/net/wlan0/type = 803
```

## UDP API

Transport:

```text
UDP/8088
device: 192.168.10.123
```

Verified commands:

```text
/status
/wifi/status
/handshakes
/aireplay?mode=test&count=1
```

Verified responses:

```text
/status -> OK airtools=1 pid=266 ?mode=all&channel=11
/wifi/status -> OK wifi ssid=AT pass_len=8 auth=WPA2PSK charset=alnum ssid_len=1..32 pass_len=8..63
/handshakes -> OK handshakes
/aireplay?mode=test&count=1 -> OK aireplay mode=test
```

Wi-Fi config endpoint:

```text
/wifi/set?ssid=<ssid>&pass=<password>
```

Validation is intentionally narrow:

```text
ssid: 1..32 chars, A-Z a-z 0-9
pass: 8..63 chars, A-Z a-z 0-9
```

Device-side validator:

```text
/bin/airwifi
```

Android-side validator mirrors the same length and alnum rules.

## Airodump / Handshake Storage

Runtime storage:

```text
/tmp/airhs
```

Observed file:

```text
/tmp/airhs/e8abfaae6ea1.pcap
```

Current design:

```text
airodump collector
  -> /tmp/airhs
```

Rules:

- One AP/BSSID keeps one latest handshake file.
- A newer handshake for the same BSSID replaces the previous one.
- AP count should be bounded by FIFO cleanup.
- `/tmp` is RAM-backed, so this storage is not persistent across power loss.

## Android Client

Project:

```text
D:\PROJECTS\AIRTOOLS
```

Known status:

```text
:app:compileDebugKotlin -> BUILD SUCCESSFUL
```

Client layer includes:

```text
AirtoolsRepository.status()
AirtoolsRepository.wifiStatus()
AirtoolsRepository.setWifi(...)
handshake list commands
generic command calls
```

Still needed on Android:

- Device/status screen.
- Capture mode controls.
- Channel/BSSID selection.
- Handshake list and download.
- Aireplay control/status screen.

## Operational Notes

BusyBox in firmware does not support every desktop option. In particular, avoid assuming `grep -E` exists in runtime diagnostics; use simpler `grep`/`sed` patterns.

The temporary TFTP server used during final flashing was stopped after verification.
