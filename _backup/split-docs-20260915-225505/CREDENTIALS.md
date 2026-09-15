# ENDOSCOPE: данные доступа

Этот файл хранит всё, что относится к логинам, паролям, hash-значениям и строкам учётных записей.
В README.md эти значения не дублировать.

## Наше устройство

### Telnet по Wi-Fi

``text
host: 192.168.10.123
port: 23
login: molink
password: molinkad
``

Подключение:

``powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-wifi.bat
``

### UART напрямую

UART shell на нашем устройстве доступен без ввода Telnet-пароля.

``text
port: COM3
speed: 57600 8N1
flow control: none
prompt: #
``

Подключение через COM3:

``powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat
``

Для другого COM-порта:

``powershell
D:\PROJECTS\ENDOSCOPE\scripts\connect-endoscope-uart.bat COM4
``

## Hash из /etc/passwd

Hash был получен на нашем устройстве через UART shell.

``text
login: molink
hash: GGyh/PXa6D1n6
hash type: classic Unix DES crypt / descrypt
hashcat mode: 1500
``

Строка /etc/passwd нашего устройства:

``text
molink:GGyh/PXa6D1n6:0:0:Adminstrator:/:/bin/sh
``

Расшифровка:

``text
uid: 0
gid: 0
comment: Adminstrator
home: /
shell: /bin/sh
``

## Hashcat

Файлы восстановления:

``text
D:\PROJECTS\ENDOSCOPE\hashcat\hash.txt
D:\PROJECTS\ENDOSCOPE\hashcat\hashcat-endoscope.potfile
D:\PROJECTS\ENDOSCOPE\hashcat\hashcat-found.txt
``

Команда просмотра результата:

``powershell
D:\PROJECTS\ENDOSCOPE\hashcat\show-result.bat
``

Параметры успешного восстановления:

``text
hashcat: 6.2.6
mode: 1500, descrypt / Traditional DES
charset: a-z0-9
length: 8
session: endoscope_molink_len8
status: Cracked
``

## Данные из внешней статьи, не от нашего устройства

Эти значения были взяты из статьи Nathan Henrie о похожем Wi-Fi эндоскопе.
На нашем устройстве они не подошли и не используются как актуальные данные входа.

``text
login: tony
password: tony4321
``
