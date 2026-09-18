from pathlib import Path
import sys, hashlib, struct, binascii, re
p=Path(sys.argv[1]); b=p.read_bytes()
print('SIZE',len(b),'SHA256',hashlib.sha256(b).hexdigest().upper())
print('HEAD',b[:64].hex(' '))
# env CRC common: first 4 little-endian or big-endian CRC32 over rest until 0xff or full sector
if len(b)>=8:
    le=struct.unpack_from('<I',b,0)[0]; be=struct.unpack_from('>I',b,0)[0]
    for n in [len(b)-4, 0x10000-4, 0x1000-4, 0x8000-4]:
        if n>0 and n+4<=len(b):
            crc=binascii.crc32(b[4:4+n]) & 0xffffffff
            print('CRC over',n,'calc',f'{crc:08X}','le_match',crc==le,'be_match',crc==be,'stored_le',f'{le:08X}','stored_be',f'{be:08X}')
# strings/kv scan
for m in re.finditer(rb'[ -~]{3,}', b):
    s=m.group().decode('ascii','replace')
    if any(k in s for k in ['BootType','bootdelay','ipaddr','serverip','ethaddr','ssid','ENDOSCOPE','192.168','baudrate','bootcmd']):
        print(f'0x{m.start():04X}: {s}')
# print first null-separated env-like area after crc, not ff
body=b[4:]
end=body.find(b'\x00\x00')
if end!=-1 and end<4096:
    print('ENV_CANDIDATE_END',end+4)
    for part in body[:end].split(b'\x00'):
        if part:
            print('ENV',part.decode('ascii','replace'))
