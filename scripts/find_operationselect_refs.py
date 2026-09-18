from pathlib import Path
import struct, hashlib
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
# Print all code references to menu strings near relative offsets.
menu = {
    'Please choose': 0x12D65,
    'Load SDRAM': 0x12D84,
    'Load write flash': 0x12DB4,
    'Boot default line': 0x12DEC,
    'Enter CLI menu': 0x12E18, # approximate? will also search real string below
    'Bootloader TFTP menu': 0x12E88,
}
# find exact strings too
for s in [b'Please choose the operation', b'Load system code to SDRAM', b'Boot system code via Flash', b'Entr boot command line', b'Load Boot Loader code then write to Flash']:
    off=b.find(s)
    print('STRING',s.decode('ascii'),hex(off), 'rel', hex(off-0x10000) if off>=0 else None)
print('=== addiu a0/base-ish immediate refs to 0x2Dxx/0x2Exx ===')
for off in range(0,len(b)-4,4):
    w=struct.unpack_from('<I',b,off)[0]
    op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
    if op==0x09 and rt==4 and 0x2d00 <= imm <= 0x2f00:
        print(f'0x{off:05X}: word=0x{w:08X} addiu a0,r{rs},0x{imm:04X}')
print('=== addiu any reg base immediate refs to menu rels exact/near ===')
rels=[]
for s in [b'Please choose the operation', b'   %d: Load system code to SDRAM', b'   %d: Boot system code via Flash', b'   %d: Entr boot command line', b'   %d: Load Boot Loader code then write to Flash']:
    off=b.find(s)
    if off>=0:
        rels.append((s.decode('ascii'), off-0x10000))
for name,rel in rels:
    print('REL',name,hex(rel))
    for off in range(0,len(b)-4,4):
        w=struct.unpack_from('<I',b,off)[0]
        op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
        if op in (0x09,0x0d) and abs(((imm if imm<0x8000 else imm-0x10000) - rel)) <= 4:
            print(f'  code 0x{off:05X}: word=0x{w:08X} op={op:02x} rt=r{rt} rs=r{rs} imm=0x{imm:04X}')
print('=== disasm around likely menu refs ===')
likely=set()
for off in range(0,len(b)-4,4):
    w=struct.unpack_from('<I',b,off)[0]
    op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
    if op==0x09 and rt==4 and 0x2d00 <= imm <= 0x2f00:
        likely.add(max(0, off-0x60))
for start in sorted(likely):
    end=start+0x180
    print(f'--- likely function around 0x{start:05X} ---')
    for insn in md.disasm(b[start:end], start):
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
