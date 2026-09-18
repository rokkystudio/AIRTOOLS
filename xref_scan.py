from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
print('xref 12208')
for i in md.disasm(b,0):
    if i.mnemonic in ('jal','bal') and ('12208' in i.op_str):
        print(hex(i.address), i.mnemonic, i.op_str)
print('ascii compare candidates')
for i in md.disasm(b,0):
    if i.mnemonic=='addiu' and '$zero, 0x33' in i.op_str:
        print('3 at',hex(i.address))
    if i.mnemonic=='addiu' and '$zero, 0x34' in i.op_str:
        print('4 at',hex(i.address))
