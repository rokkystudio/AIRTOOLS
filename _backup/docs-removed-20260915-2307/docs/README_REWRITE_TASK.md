# Задание для другой ветки чата: компактный README проекта ENDOSCOPE

Рабочий каталог: D:\PROJECTS\ENDOSCOPE

Перед любыми изменениями обязательно сделать backup README:

    $root = 'D:\PROJECTS\ENDOSCOPE'
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    New-Item -ItemType Directory -Force "$root\_backup" | Out-Null
    Copy-Item -LiteralPath "$root\README.md" -Destination "$root\_backup\README-before-rewrite-$stamp.md" -Force

Цель: собрать нормальный компактный README.md без раздувания и без полного копирования логов.

Нельзя удалять или перезаписывать без отдельного разрешения:

- hashcat\
- logs\
- images\
- dumps\
- _backup\

Особенно не трогать файлы результата восстановления доступа в hashcat\.
Не выдумывать и не менять секреты. Брать значения только из существующих файлов проекта. В итоговом README лучше ссылаться на локальный файл результата, а не дублировать секрет открытым текстом.

Желаемая структура README:

1. Назначение проекта.
2. Быстрый доступ: SSID, IP, Telnet, скрипт подключения.
3. Аппаратная часть: PCB, SoC, RAM, flash, UART.
4. Разметка flash из /proc/mtd.
5. Сетевые сервисы.
6. Кратко про восстановление доступа: источник, режим hashcat, charset, длина, где лежит результат.
7. Структура каталогов.
8. Ссылки на похожий reverse engineering.
9. Следующие шаги: проверить Telnet, сделать полный backup flash, разобрать TCP/7060, не писать во flash до backup.

Ограничение: итоговый README примерно 100-180 строк максимум.
