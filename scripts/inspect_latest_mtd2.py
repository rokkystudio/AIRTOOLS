from pathlib import Path
import sys, hashlib, struct, binascii, re
p=Path(sys.argv[1]); b=p.read_bytes()
print('SIZE',len(b),'SHA256',hashlib.sha256(b).hexdigest().upper())
print('ALL_FF', all(x==0xff for x in b), 'ALL_00', all(x==0 for x in b))
print('HEAD',b[:32].hex(' '))
print('TAIL',b[-32:].hex(' '))
if len(b)>=4:
    le=struct.unpack_from('<I',b,0)[0]; be=struct.unpack_from('>I',b,0)[0]
    for n in [len(b)-4,0x10000-4,0x8000-4,0x4000-4,0x1000-4]:
        if 4+n <= len(b):
            crc=binascii.crc32(b[4:4+n]) & 0xffffffff
            print('CRC',n,f'calc={crc:08X}',f'le={le:08X}',f'be={be:08X}','le_match',crc==le,'be_match',crc==be)
print('FIRST NON FF', next((i for i,x in enumerate(b) if x!=0xff), None))
print('FIRST NON 00 AFTER NONFF', next((i for i,x in enumerate(b) if x not in (0xff,0x00)), None))
print('STRINGS KEY')
for m in re.finditer(rb'[ -~]{3,}', b):
    s=m.group().decode('ascii','replace')
    if any(k in s for k in ['BootType','bootdelay','ipaddr','serverip','ethaddr','ssid','ENDOSCOPE','192.168','baudrate','bootcmd','OperationMode','HostName','lan_ipaddr']):
        print(f'0x{m.start():04X}: {s}')
print('FIRST STRINGS')
c=0
for m in re.finditer(rb'[ -~]{4,}', b):
    print(f'0x{m.start():04X}: {m.group()[:80].decode("ascii","replace")}')
    c+=1
    if c>40: break
