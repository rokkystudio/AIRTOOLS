from pathlib import Path
import sys, hashlib, struct, binascii, re
p=Path(sys.argv[1]); b=p.read_bytes()
print('SIZE',len(b),'SHA256',hashlib.sha256(b).hexdigest().upper())
print('HEAD',b[:64].hex(' '))
le=struct.unpack_from('<I',b,0)[0]; be=struct.unpack_from('>I',b,0)[0]
for n in [len(b)-4,0x10000-4,0x1000-4,0x8000-4]:
    if 4+n <= len(b):
        crc=binascii.crc32(b[4:4+n]) & 0xffffffff
        print('CRC',n,f'calc={crc:08X}',f'le={le:08X}',f'be={be:08X}','le_match',crc==le,'be_match',crc==be)
print('STRINGS')
for m in re.finditer(rb'[ -~]{3,}', b):
    s=m.group().decode('ascii','replace')
    if any(k in s for k in ['BootType','bootdelay','ipaddr','serverip','ethaddr','ssid','ENDOSCOPE','192.168','baudrate','bootcmd']): print(f'0x{m.start():04X}: {s}')
end=b[4:].find(b'\x00\x00')
if 0 <= end < 4096:
    print('ENV_END',end+4)
    for part in b[4:4+end].split(b'\x00'):
        if part: print('ENV',part.decode('ascii','replace'))
