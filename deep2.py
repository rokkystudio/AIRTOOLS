from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
print('GP BASE 4338')
for i in md.disasm(b,0):
    if i.mnemonic=='addiu' and '$gp' in i.op_str and '0x4338' in i.op_str:
        print(hex(i.address),i.op_str)
print('JALR TABLE LOADS')
ins=list(md.disasm(b,0))
for n,i in enumerate(ins[:-2]):
    if i.mnemonic=='lw' and '$t9' in i.op_str and '(gp)' in i.op_str:
        if ins[n+2].mnemonic=='jalr':
            print(hex(i.address),i.op_str,'call',hex(ins[n+2].address))
print('STRINGS')
for s in [b'BootType',b'bootm bc050000',b'System Boot system code via Flash']:
 print(s,b.find(s))
