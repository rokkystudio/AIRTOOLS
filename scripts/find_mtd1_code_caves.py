from pathlib import Path
import hashlib, re, struct
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/'dumps/original/mtd1_bootloader.bin').read_bytes()
print('SIZE',len(b),'SHA256',hashlib.sha256(b).hexdigest().upper())
# Find free regions: all FF or all 00 long enough inside bootloader partition
for val,name in [(0xff,'FF'),(0x00,'00')]:
    runs=[]; i=0
    while i<len(b):
        if b[i]==val:
            j=i
            while j<len(b) and b[j]==val: j+=1
            if j-i>=64: runs.append((i,j-i))
            i=j
        else:i+=1
    print('RUNS',name,'count',len(runs))
    for off,l in runs[:20]: print(f'  0x{off:05X} len=0x{l:X}')
# function starts: pattern gp prolog after code - free text nearby
print('last non-ff', max(i for i,x in enumerate(b) if x!=0xff))
# Print strings 0x135a0 onwards and unused tail
for m in re.finditer(rb'[ -~]{4,}', b):
    if m.start()>=0x13500:
        print(f'STR 0x{m.start():05X}: {m.group()[:100].decode("ascii","replace")}')
# Search nops / zero code cave between functions
runs=[]; i=0
while i < len(b):
    if b[i:i+4]==b'\x00\x00\x00\x00':
        j=i
        while j+4<=len(b) and b[j:j+4]==b'\x00\x00\x00\x00': j+=4
        if j-i>=32: runs.append((i,j-i))
        i=j
    else: i+=4
print('NOP zero aligned runs >=32')
for off,l in runs[:50]: print(f' 0x{off:05X} len=0x{l:X}')
