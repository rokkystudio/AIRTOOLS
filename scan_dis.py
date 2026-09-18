from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_MIPS32)
for start,end in [(0,0x1000),(0x1000,0x1200),(0x10000,0x11000)]:
 print('---',hex(start))
 for i in md.disasm(b[start:end],start):
  if i.mnemonic in ('lui','addiu','addi','jal','jalr','jr','lw','sw','beq','bne'):
   print(f'{i.address:08x}: {i.mnemonic:5} {i.op_str}')
