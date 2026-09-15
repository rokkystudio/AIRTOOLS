# ENDOSCOPE: данные доступа

Этот файл хранит всё, что относится к логинам, паролям, hash-значениям, строкам учётных записей и восстановлению штатного Telnet-доступа.
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

Подключение:

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

На нашем устройстве отдельные shadow-файлы не найдены. Hash находился прямо в файле учётных записей.

## Как восстанавливали доступ по Telnet

Hash был сохранён в:

``text
D:\PROJECTS\ENDOSCOPE\hashcat\hash.txt
``

Использовался hashcat:

``text
hashcat: 6.2.6
mode: 1500, descrypt / Traditional DES
GPU: NVIDIA GeForce RTX 3060 Ti
charset: a-z0-9
``

Сначала был перебран диапазон длины 1..6:

``text
session: endoscope_molink_len1_6
status: Exhausted
recovered: 0/1
``

Затем был запущен перебор длины 7, после чего успешный результат был получен на длине 8:

``text
session: endoscope_molink_len8
status: Cracked
recovered: 1/1
speed: about 1274 MH/s
progress at crack: about 22.15% of full length-8 keyspace
``

Просмотр результата:

``powershell
D:\PROJECTS\ENDOSCOPE\hashcat\show-result.bat
``

Файлы восстановления:

``text
D:\PROJECTS\ENDOSCOPE\hashcat\hash.txt
D:\PROJECTS\ENDOSCOPE\hashcat\hashcat-endoscope.potfile
D:\PROJECTS\ENDOSCOPE\hashcat\hashcat-found.txt
D:\PROJECTS\ENDOSCOPE\hashcat\run-len1-6.bat
D:\PROJECTS\ENDOSCOPE\hashcat\run-len7.bat
D:\PROJECTS\ENDOSCOPE\hashcat\run-len8.bat
D:\PROJECTS\ENDOSCOPE\hashcat\show-result.bat
``

## Данные из внешней статьи, не от нашего устройства

Эти значения были взяты из статьи Nathan Henrie о похожем Wi-Fi эндоскопе. На нашем устройстве они не подошли и не используются как актуальные данные входа.

``text
login: tony
password: tony4321
``

