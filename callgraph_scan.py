from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
print('possible address constructions for 0x12208')
for i in md.disasm(b,0):
    if i.mnemonic in ('lui','addiu','ori') and ('0x12208' in i.op_str or '0x2208' in i.op_str or '0x1220' in i.op_str):
        print(hex(i.address),i.mnemonic,i.op_str)
print('jalr with nearby function pointer loads around 12000-15000')
for i in md.disasm(b[0x12000:0x15000],0x12000):
    if i.mnemonic=='jalr':
        print(hex(i.address),i.mnemonic,i.op_str)
