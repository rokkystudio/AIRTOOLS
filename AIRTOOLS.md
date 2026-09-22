# AIRTOOLS платформа

Текущая архитектура управления AIRTOOLS: management AP `AT`, отдельный WN723N/RTL8188EUS в monitor mode, TCP control API и Android-клиент `D:\PROJECTS\AIRTOOLS-APP`.

## Проверенная прошивка

Последний физически проверенный образ:

```text
dumps\verified\mtd4_airtools_tcp_scan_20260922.bin
size=3866624
sha256=ab20813ee4bb9f58a96ec5c246431af901ec0249f3d645c17bcda74195d05673
```

Образ физически проверен: boot, management AP, TCP/8088, Android reconnect, SCAN, channel hopping и выдача найденных сетей.

Текущий TCP-кандидат:

```text
dumps\modified\mtd4_base_connectivity_wn723n_autostart_airtools.bin
size=3866624
sha256=ab20813ee4bb9f58a96ec5c246431af901ec0249f3d645c17bcda74195d05673
```

Важно: Linux `SOCK_STREAM=1`, `SOCK_DGRAM=2`. Ошибочные значения блокировали работу нового TCP `/bin/airtools`; исправлено до сборки этого кандидата.

## Management network

Management AP остается пользовательской точкой подключения. Android-приложение не вводит и не меняет пароль Wi-Fi.

```text
service IP: 192.168.10.123
control: TCP/8088
```

IP и port являются внутренними параметрами и в пользовательском статусе Android не показываются.

## TCP API

`/bin/airtools` принимает одну текстовую команду на TCP connection, отправляет ответ и закрывает connection.

```text
/status
/set?mode=bssid&bssid=<mac>&channel=<n>
/start
/stop
/scan/start
/scan/stop
/networks
/handshakes
/aireplay?mode=test&count=1
```

`/set` только сохраняет target. Capture запускается только через `/start` и останавливается через `/stop`.

`/status` возвращает состояние capture и discovery scan:

```text
OK airtools=1 pid=<capture_pid> scan=<0|1> ?mode=<all|bssid>...&channel=<n>
state_path=/tmp/airtools.state
```

## Выбор Wi-Fi target

Экран `SCAN` запускает `/scan/start`. Во время discovery WN723N переключается по каналам 1..13, а `airodump` накапливает найденные AP.

Runtime index:

```text
/tmp/airscan-networks.txt
# bssid,channel,beacons,probes,data,essid
```

`/networks` возвращает список. После выбора AP Android вызывает `/scan/stop`, сохраняет BSSID/channel/ESSID и возвращается на главный экран.

## Capture

Главный экран имеет одну кнопку `START/STOP`.

`START` выполняет:

```text
/set?mode=bssid&bssid=<selected>&channel=<selected>
/start
```

`STOP` выполняет `/stop`. Capture не стартует автоматически при запуске `/bin/airtools`.

## Handshake storage

```text
/tmp/airhs
/tmp/airhs/index.txt
```

Один BSSID хранит один последний handshake PCAP. Новый handshake заменяет предыдущий для того же BSSID. Storage находится в `/tmp` и не переживает power cycle. `/handshakes` возвращает текущий index. Передача самого `.pcap` через control API еще не реализована.

## Android client

Проект: `D:\PROJECTS\AIRTOOLS-APP`.

Текущее поведение:

- TCP client вместо UDP;
- `/status` автоматически проверяется примерно раз в секунду;
- отдельной кнопки `REFRESH` нет;
- приложение автоматически восстанавливает TCP-связь;
- TCP sockets привязываются к физической Wi-Fi network (`NOT_VPN`), чтобы активный Android VPN не перехватывал management traffic;
- IP/port в пользовательском статусе не показываются;
- статус: цветной круг + короткая строка;
- зеленый — `Устройство подключено`;
- желтый — `Подключение к устройству`;
- красный — `Ошибка подключения`;
- серый — `Сервер недоступен`;
- Wi-Fi password/config UI отсутствует;
- `SCAN` открывает экран выбора target AP;
- `START/STOP` — одна stateful-кнопка;
- выбранный BSSID/channel/ESSID сохраняется локально на Android;
- верхняя панель использует launcher icon AIRTOOLS, light/dark и RU/EN controls.

`assembleDebug` проходит. Полная end-to-end проверка нового TCP API требует физической проверки нового `mtd4` candidate.