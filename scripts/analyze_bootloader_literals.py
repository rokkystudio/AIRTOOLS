from pathlib import Path
import hashlib, struct, re
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
print('BOOT size', len(b), 'sha256', hashlib.sha256(b).hexdigest().upper())
print('=== all 0x1B byte contexts ===')
for off,x in enumerate(b):
    if x==0x1b:
        start=max(0, off-16); end=min(len(b), off+17)
        print(f'0x{off:05X}:', b[start:end].hex(' '), 'ascii=', ''.join(chr(c) if 32<=c<127 else '.' for c in b[start:end]))
print('=== words containing imm 0x001b both endian / all opcodes ===')
for endian,fmt in [('LE','<I'),('BE','>I')]:
    print('---', endian, '---')
    cnt=0
    for off in range(0, len(b)-4, 4):
        w=struct.unpack_from(fmt,b,off)[0]
        if (w & 0xffff)==0x001b:
            op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
            print(f'0x{off:05X}: 0x{w:08X} op=0x{op:02X} rs={rs} rt={rt} imm=0x{imm:04X}')
            cnt+=1
    print('count',cnt)
print('=== words containing imm 0x0033 or 0x0034 or ascii 3/4 context candidates ===')
for endian,fmt in [('LE','<I'),('BE','>I')]:
    print('---',endian,'---')
    for immv in [0x1b,0x33,0x34,0x30,0x35,0x37,0x38,0x39]:
        offs=[]
        for off in range(0,len(b)-4,4):
            w=struct.unpack_from(fmt,b,off)[0]
            if (w&0xffff)==immv:
                offs.append(off)
        if offs:
            print(f'imm {immv:04x}', [f'0x{o:05X}' for o in offs[:30]], 'count',len(offs))
# Try import capstone
print('=== python modules ===')
try:
    import capstone
    print('capstone available', capstone.__version__)
except Exception as e:
    print('capstone not available', type(e).__name__, e)
