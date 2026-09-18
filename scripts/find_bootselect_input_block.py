from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
strings=[b'You choosed',b'choosed',b'Please choose',b'Operation terminated',b'bootdelay',b'BootType',b'default: %c',b'\b\b\b%2d']
for s in strings:
    off=b.find(s)
    print('STRING',s, 'off', hex(off) if off>=0 else None, 'rel', hex(off-0x10000) if off>=0 else None)
print('=== all printable strings 0x12d00-0x13600 ===')
import re
for m in re.finditer(rb'[ -~]{4,}', b[0x12d00:0x13650]):
    print(f'0x{0x12d00+m.start():05X}:', m.group().decode('ascii','replace'))
print('=== refs near BootType/default strings ===')
rels=[]
for s in [b'bootdelay',b'BootType',b'default: %c',b'You choosed',b'\b\b\b%2d']:
    off=b.find(s)
    if off>=0:
        rels.append((s.decode('ascii','replace'),off-0x10000))
for name,rel in rels:
    print('REL',name,hex(rel))
    for off in range(0,len(b)-4,4):
        w=struct.unpack_from('<I',b,off)[0]
        op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
        simm=imm if imm<0x8000 else imm-0x10000
        if op in (0x09,0x0d) and abs(simm-rel)<=4:
            print(f'  0x{off:05X}: w=0x{w:08X} op={op:02x} rt={rt} rs={rs} imm=0x{imm:04X}')
print('=== concise main bootselect 0x020E0-0x02280 ===')
for insn in md.disasm(b[0x020e0:0x02280],0x020e0):
    print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
