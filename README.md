# ENDOSCOPE

Рабочий проект по исследованию и модификации старого Wi-Fi эндоскопа.

## Главные файлы

- [DEVICE.md](DEVICE.md) — проверенные характеристики нашего экземпляра.
- [SYSTEM.md](SYSTEM.md) — общая информация о Linux, прошивке и сервисах.
- [CREDS.md](CREDS.md) — данные доступа и восстановление Telnet.
- [TONY.md](TONY.md) — заметки по внешней статье о похожем устройстве.

## Быстрый старт

### Wi-Fi / Telnet

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-wifi.bat
```

Локальные Telnet-параметры для автоматизации находятся в:

```text
agent\endoscope-telnet.local.ps1
```

Запуск одной команды:

```powershell
D:\PROJECTS\ENDOSCOPE\agent\run-endoscope-telnet-command.bat "cat /proc/cpuinfo"
```

### UART

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat
```

Для другого COM-порта:

```powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat COM4
```

## Структура проекта

```text
README.md                  краткий указатель по проекту
DEVICE.md                  характеристики экземпляра
SYSTEM.md                  общая информация о Linux/firmware
CREDS.md                   данные доступа
TONY.md                    заметки по внешней статье

images\                    фотографии платы
dumps\                     полный flash dump и MTD-разделы
hashcat\                   hash input, potfile, result и run-len1-8.bat
scripts\                   ручные BAT-скрипты подключения
agent\                     Telnet automation
```

## Flash backup

Полный backup SPI flash уже снят и хранится в:

```text
dumps\flash_full_mtd0.bin
```

Разделы также сохранены отдельно:

```text
dumps\mtd1_bootloader.bin
dumps\mtd2_config.bin
dumps\mtd3_factory.bin
dumps\mtd4_kernel.bin
```

Подробности и SHA256 находятся в [DEVICE.md](DEVICE.md).

## Hashcat

В `hashcat\` оставлен один launch-файл:

```text
hashcat\run-len1-8.bat
```

Он запускает mask attack для длин от 1 до 8 символов с charset `?l?d`.

Остальные файлы каталога:

```text
hash.txt
hashcat-endoscope.potfile
hashcat-found.txt
```

## Текущий статус

Устройство доступно:

- через UART shell;
- по Telnet через Wi-Fi.

Сохранён полный flash dump, а общая карта Linux-системы находится в [SYSTEM.md](SYSTEM.md).

При экспериментах с Wi-Fi, NVRAM или flash UART следует держать как recovery-канал.

## Дальше

1. Перед постоянными изменениями использовать сохранённый flash dump как recovery backup.
2. Изменения Wi-Fi и flash выполнять только при доступном UART recovery.
3. По мере экспериментов обновлять `DEVICE.md` и `SYSTEM.md`.
