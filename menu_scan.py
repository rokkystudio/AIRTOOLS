from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
for start in [0x12000,0x12400,0x12800,0x12c00,0x13000]:
 print('---',hex(start))
 for i in md.disasm(b[start:start+0x400],start):
  if i.mnemonic in ('jal','jalr','beq','bne','lui','addiu','lw','sw','lb','lbu','jr'):
   print(f'{i.address:08x}: {i.mnemonic:5} {i.op_str}')
