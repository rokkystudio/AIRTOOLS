from pathlib import Path
from capstone import *
b=Path('dumps/original/mtd1_bootloader.bin').read_bytes()
for s in [b'BootType', b'default: %c', b'bootdelay', b'Please choose the operation']:
    off=b.find(s)
    print('STRING',s,hex(off))
    print(b[max(0,off-32):off+len(s)+32].hex())
md=Cs(CS_ARCH_MIPS,CS_MODE_MIPS32+CS_MODE_LITTLE_ENDIAN)
md.detail=True
hits=[]
for i in md.disasm(b,0):
    if 'gp' in i.op_str and i.mnemonic in ('addiu','addi','ori','lui'):
        hits.append((i.address,i.mnemonic,i.op_str))
print('GP')
for x in hits[:100]: print(hex(x[0]),x[1],x[2])
print('count',len(hits))
