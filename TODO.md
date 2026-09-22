# Open Tasks

Актуальный список незакрытых задач после финальной проверки WPA2 `AT` + airtools.

## P1 - Real Handshake Capture

Проверить полный цикл настоящего WPA handshake:

- capture на `wlan0` monitor;
- один BSSID;
- несколько клиентов одного AP;
- новый handshake заменяет старый для этого BSSID;
- `/handshakes` показывает актуальный список;
- `.pcap` можно скачать/перенести и открыть внешним инструментом.

Готово, когда есть сохраненный тестовый `.pcap`, команда `/handshakes` возвращает ожидаемый index, а поведение replacement проверено минимум двумя capture-событиями.

## P1 - Runtime State Persistence

Сейчас режим airodump/airtools живет в runtime и сбрасывается после питания.

Нужно выбрать безопасный persistence-механизм:

- не писать `mtd2/mtd3` без отдельного анализа;
- не ломать recovery;
- явно описать формат и место хранения;
- проверить power-cycle.

Варианты для анализа: config внутри `mtd4`, отдельный reserved offset, маленький generated file в rootfs на этапе сборки.

## P2 - Android UI

В `D:\PROJECTS\AIRTOOLS` уже есть клиентский слой и `compileDebugKotlin OK`.

Осталось:

- экран устройства/status;
- статус Wi-Fi подключения;
- выбор режима capture: all/channel/BSSID;
- список handshakes;
- загрузка `.pcap`;
- экран Wi-Fi config;
- обработка ошибок UDP/timeout.

## P2 - Aireplay Integration

Сейчас проверен только:

```text
/aireplay?mode=test&count=1 -> OK aireplay mode=test
```

Осталось:

- команды start/stop;
- runtime status;
- защита от параллельных запусков;
- понятные ошибки API;
- Android control/status.

## P3 - RTL8188EUS Driver Cleanup

Текущий результат рабочий, но ветка драйвера остается технически хрупкой.

Направления:

- найти MediaTek/Ralink MT7628 vendor SDK под Linux 2.6.36;
- найти более старый Realtek 8188eu driver эпохи 2.6.36;
- задокументировать текущие ABI-патчи;
- минимизировать локальные хаки;
- собрать clean rebuild procedure.

Эта задача не блокирует текущую AIRTOOLS-платформу.

## P3 - Documentation Follow-Up

- После реального handshake test обновить [AIRTOOLS.md](AIRTOOLS.md).
- После persistence-решения обновить [FIRMWARE.md](FIRMWARE.md) и [BRICK.md](BRICK.md), если появится запись во flash.
- Старые failed build logs не переносить в главные md; при необходимости сохранять только краткие выводы в `HISTORY*.md`.
