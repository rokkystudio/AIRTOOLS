# AIRTOOLS платформа

AIRTOOLS состоит из устройства на MT7628 с отдельным TP-Link WN723N/RTL8188EUS в monitor mode, management AP `AT`, TCP control API и Android-клиента `D:\PROJECTS\AIRTOOLS-APP`.

## Проверенная прошивка

Текущий физически проверенный `mtd4`:

```text
dumps\verified\mtd4_airtools_mode_signal_20260923.bin
size=3866624
sha256=145413bdc96f95bcfe59c814f396ee1f0f45a4d3f8c6a08e37cf44e7de59c6ef
```

Проверено на реальном устройстве: boot, management AP, TCP/8088, автоматический discovery scan, channel hopping 1..13, RSSI из radiotap, сортировка Android по уровню сигнала, атомарный переход scan -> capture, фильтрация capture по BSSID/channel, возврат capture -> scan и восстановление экрана Android по `/status` после перезапуска приложения.

Текущий build output совпадает с проверенным образом:

```text
dumps\modified\mtd4_base_connectivity_wn723n_autostart_airtools.bin
size=3866624
sha256=145413bdc96f95bcfe59c814f396ee1f0f45a4d3f8c6a08e37cf44e7de59c6ef
```

## Management network

Management AP используется только как канал управления. Android не меняет его Wi-Fi конфигурацию.

```text
service IP: 192.168.10.123
control: TCP/8088
```

Android TCP sockets привязываются к физической Wi-Fi network с `NOT_VPN`, чтобы активный VPN телефона не перехватывал management traffic.

## TCP API

`/bin/airtools` принимает одну текстовую команду на TCP connection, отправляет ответ и закрывает connection.

Перед `exec` дочерние `airodump`/`aireplay` процессы и discovery hopper закрывают унаследованные control server/client descriptors. Поэтому worker не удерживает TCP/8088 после остановки или перезапуска `airtools`.

```text
/status
/scan/start
/scan/stop
/networks
/select?bssid=<mac>&channel=<n>
/set?mode=bssid&bssid=<mac>&channel=<n>
/start
/stop
/handshakes
/aireplay?mode=test&count=1
```

Основной Android flow использует `/scan/start`, `/networks`, `/select`, `/status` и `/handshakes`. `/set`, `/start` и `/stop` остаются низкоуровневыми командами.

`/select` выполняет переход режима на устройстве атомарно: сохраняет BSSID/channel, останавливает discovery hopper и discovery `airodump`, переводит `wlan0` на выбранный канал и запускает `airodump` с фильтром выбранного BSSID.

`/status` возвращает фактический runtime state:

```text
OK airtools=1 mode=<idle|scan|capture> pid=<capture_pid> scan=<0|1> ?mode=<all|bssid>...&channel=<n>
state_path=/tmp/airtools.state
```

Поле `mode` является явным runtime-режимом устройства: `idle`, `scan` или `capture`. Android строит экран по нему, а не выводит режим косвенно из PID или сохранённого target.

## Discovery scan и RSSI

Discovery запускает один `airodump 0 all`. Monitor mode включается один раз, после чего отдельный hopper переключает `wlan0` по каналам 1..13 через `iwconfig`, не пересоздавая monitor interface.

Runtime index:

```text
/tmp/airscan-networks.txt
# bssid,channel,signal_dbm,beacons,probes,data,essid
```

`signal_dbm` извлекается из radiotap `DBM_ANTSIGNAL`. Android не сортирует список по единичному RSSI: для каждого BSSID ведётся окно из пяти новых измерений, среднее используется для индикации и сортировки. Новое измерение добавляется только когда меняются Beacon/Probe/Data counters, поэтому повторное чтение одного snapshot не искажает среднее. Если counters сети не меняются 12 секунд, сеть считается Offline и уходит в конец списка; после появления новых кадров она автоматически возвращается в online.

## Android flow

Отдельного экрана `SCAN`, кнопки `SCAN` и кнопки `START/STOP` больше нет.

После запуска приложение автоматически запрашивает `/status`. Если устройство сканирует, показывается список Wi-Fi сетей. Если уже идёт target capture, сразу показывается выбранная сеть. Если устройство сообщает `idle`, Android запускает discovery scan. Выход из приложения не переводит работающий `scan` или `capture` в `idle`.

Во время scan список обновляется автоматически. Каждая карточка показывает ESSID, BSSID, канал, усреднённый RSSI в dBm, процент и пятиступенчатую иконку уровня: Excellent, Very Good, Good, Fair, Poor или Offline. Цветные ступени соответствуют уровню сигнала, Offline отображается полностью серой иконкой. Online-сети сортируются по плавающему среднему RSSI, Offline располагаются внизу.

Нажатие на сеть сразу вызывает `/select`; отдельный START не нужен. После успешного перехода Android показывает только выбранную сеть и live capture details: BSSID, channel, RSSI, Beacon/Probe/Data counters и состояние WPA handshake.

Кнопка Back в верхней панели вызывает `/scan/start`, то есть реально переводит устройство обратно из target capture в discovery scan и возвращает Android к списку сетей.

Выход из Android приложения не меняет режим устройства. При следующем запуске экран восстанавливается по фактическому `/status`, а не по предположению Android.

Connection status намеренно простой: зелёный только при успешном `/status`; подключение и недоступность устройства отображаются серым. Кратковременный единичный TCP failure после уже установленной связи не переключает UI в unavailable — требуется несколько последовательных ошибок.

## Capture и handshake storage

При выбранной сети `airodump` работает как:

```text
airodump 0 bssid <selected-bssid> channel <selected-channel>
```

Handshake storage:

```text
/tmp/airhs
/tmp/airhs/index.txt
```

Один BSSID хранит один последний handshake PCAP. Новый handshake заменяет предыдущий для того же BSSID. `/handshakes` возвращает index; Android показывает live состояние handshake на экране выбранной сети. Передача самого `.pcap` через control API пока не реализована.

## Flash safety

Обычные firmware изменения относятся только к `Kernel/mtd4`. Без отдельного решения нельзя писать `mtd1` Bootloader, `mtd2` Config и `mtd3` Factory.

Перед reboot после flash нужно проверить содержимое записанного `mtd4`; для текущего образа физическая проверка дала `FLASH_OK`.