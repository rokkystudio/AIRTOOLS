from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
for start,end in [(0x01f00,0x02280),(0x02080,0x021c0),(0x01d00,0x02100),(0x0e700,0x0e860),(0x0f400,0x0f480)]:
    print(f'=== DISASM 0x{start:05X}-0x{end:05X} ===')
    for insn in md.disasm(b[start:end], start):
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
# Search exact instructions that set s5 ($21) to 0x33 or store/load s5 around bootselect region
print('=== instructions immediate 0x33 to s5/v regs ===')
for off in range(0,len(b)-4,4):
    w=struct.unpack_from('<I',b,off)[0]
    op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
    if imm==0x33 and op in (0x09,0x0d):
        print(f'0x{off:05X}: word=0x{w:08X} op={op:02x} rs={rs} rt={rt}')
print('=== calls to tstc/getc likely around 0x20xx via gp offsets ===')
# just print lw t9 gp offsets and jalr in bootselect area
for insn in md.disasm(b[0x01f00:0x02280],0x01f00):
    if '$t9' in insn.op_str or insn.mnemonic in ('jalr','beq','bne','beqz','bnez'):
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
