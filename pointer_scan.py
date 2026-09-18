from pathlib import Path
import struct
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
vals=[0x12208,0x80012208,0xBFC12208,0x13240,0x1324c,0x13258,0x12d65]
for v in vals:
 print('VALUE',hex(v))
 for endian in ['<','>']:
  p=struct.pack(endian+'I',v)
  hits=[]
  off=0
  while True:
   off=b.find(p,off)
   if off<0: break
   hits.append(hex(off)); off+=1
  print(endian,hits[:20], 'count',len(hits))
print('ascii refs')
for s in [b'BootType',b'default: %c',b'bootdelay',b'Please choose']:
 print(s,hex(b.find(s)))
