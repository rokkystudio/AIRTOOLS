from pathlib import Path
import re, hashlib
boot=Path(r'D:\PROJECTS\ENDOSCOPE\dumps\original\mtd1_bootloader.bin')
b=boot.read_bytes()
print('BOOT_SIZE', len(b), 'SHA256', hashlib.sha256(b).hexdigest().upper())
strings=[]
for m in re.finditer(rb'[ -~]{4,}', b):
    s=m.group().decode('ascii','replace')
    if any(x in s for x in ['System Boot','Boot','default','Operation','Load','Flash','MT7628','Linux','Please','Press','4:', '3:', 'U-Boot']):
        strings.append((m.start(),s))
for off,s in strings:
    print(f'0x{off:05X}: {s}')
