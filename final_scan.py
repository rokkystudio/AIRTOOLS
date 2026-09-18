from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
ins=list(md.disasm(b,0))
print('STRING BUILDERS')
for i in ins:
    if i.mnemonic in ('lui','addiu','ori'):
        if any(x in i.op_str for x in ['0x132','0x324','0x240']):
            print(hex(i.address),i.mnemonic,i.op_str)
print('A0 STRING OFFSETS')
for i in ins:
    if i.mnemonic in ('addiu','ori') and '$a0' in i.op_str:
        if any(x in i.op_str for x in ['0x5a','0x32','0x24']):
            print(hex(i.address),i.mnemonic,i.op_str)
