from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
print('GP SETUP')
for i in md.disasm(b,0):
    if i.mnemonic=='addiu' and '$gp' in i.op_str:
        print(hex(i.address), i.op_str)
print('COMPARES 33/34')
for i in md.disasm(b,0):
    if i.mnemonic in ('addiu','ori') and ('0x33' in i.op_str or '0x34' in i.op_str):
        print(hex(i.address),i.mnemonic,i.op_str)
