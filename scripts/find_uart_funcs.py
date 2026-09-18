from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/'dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
# find lui reg,0xb018 / 0xb000 / uart-ish around 0x28xx and functions that return char
print('=== occurrences of lui *,0xb018 ===')
for off in range(0,len(b)-4,4):
    w=struct.unpack_from('<I',b,off)[0]
    if (w>>26)==0x0f and (w & 0xffff)==0xb018:
        rt=(w>>16)&31
        print(f'0x{off:05X}: word=0x{w:08X} rt={rt}')
for start in [0x02898,0x02918,0x02980,0x02a00,0x02a80,0x02b00,0x02b80,0x02c00,0x02c80,0x02d00,0x02d80,0x0a400,0x0a480,0x0a500]:
    print(f'--- disasm 0x{start:05X}-0x{start+0x100:05X} ---')
    for insn in md.disasm(b[start:start+0x100],start):
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
# search callers of gp offsets maybe table: calls to 0x350 (getc), 0x340 maybe tstc, 0x324 puts?
print('=== gp lw offsets around calls summary ===')
from collections import Counter
cnt=Counter()
for off in range(0,len(b)-8,4):
    w=struct.unpack_from('<I',b,off)[0]
    op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
    if op==0x23 and rs==28 and rt==25: # lw t9, imm(gp)
        cnt[imm]+=1
for imm,n in sorted(cnt.items(), key=lambda x:x[0]):
    if imm in [0x340,0x350,0x3d8,0x324,0x374,0x158,0x17c,0x1d8,0x12c]:
        print(f'gp+0x{imm:03X}: count {n}')
        for off in range(0,len(b)-8,4):
            w=struct.unpack_from('<I',b,off)[0]
            op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; im=w&0xffff
            if op==0x23 and rs==28 and rt==25 and im==imm:
                print(f'  lw at 0x{off:05X}')
