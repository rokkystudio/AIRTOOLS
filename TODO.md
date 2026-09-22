# Open Tasks

Актуальные незакрытые задачи AIRTOOLS после перехода control plane на TCP и нового Android flow.

## P1 — Real Handshake Capture

Проверить полный цикл настоящего WPA handshake на выбранном BSSID:

- capture на `wlan0` monitor;
- несколько клиентов одного AP;
- новый handshake заменяет старый для того же BSSID;
- `/handshakes` возвращает актуальный index;
- сохраненный `.pcap` открывается внешним анализатором.

## P1 — PCAP download

Сейчас TCP API возвращает handshake index, но не сам файл. Нужен бинарный download endpoint и Android-сохранение `.pcap` без промежуточного Hashcat flow.

## P1 — Runtime State Persistence

`/tmp/airtools.state`, network discovery index и handshake storage не переживают power cycle. Если persistence действительно нужен, выбрать безопасное место только после отдельного анализа. `mtd2/mtd3` не использовать без отдельного решения.

## P2 — Aireplay Integration

Тестовый endpoint существует. Для полноценного управления еще нужны runtime status, защита от параллельных запусков и Android controls для разрешенных режимов.

## P3 — RTL8188EUS Driver Cleanup

Рабочий driver остается технически хрупким. Дальше: найти более подходящий vendor SDK/старый 8188eu под Linux 2.6.36, задокументировать ABI patches и получить чистую воспроизводимую сборку.