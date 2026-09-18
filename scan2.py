from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
ins=list(md.disasm(b,0))
print('near string address offsets in immediate values')
for i in ins:
    for val in ['0x4c','0x58','0x77','0x240','0x24c','0x258','0x277']:
        if val in i.op_str:
            print(hex(i.address),i.mnemonic,i.op_str)
print('all jalr functions around 0x10000-0x18000 with preceding t9 load')
for n,i in enumerate(ins):
    if 0x10000<=i.address<=0x18000 and i.mnemonic=='jalr':
        print(hex(i.address))
