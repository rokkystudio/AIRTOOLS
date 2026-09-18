from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
for target in [0x1324c,0x13258,0x13240,0x12d65]:
 print('TARGET',hex(target))
 for i in md.disasm(b,0):
  if i.address>0x30000: break
  if hex(target & 0xffff) in i.op_str or hex((target>>16)&0xffff) in i.op_str:
   print(hex(i.address),i.mnemonic,i.op_str)
print('near menu strings')
for off in range(0x12000,0x14000):
 if b[off:off+10] == b'Please cho': print(hex(off))
