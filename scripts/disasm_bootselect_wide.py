from pathlib import Path
import struct
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/'dumps/original/mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
print('=== bootselect wider 0x01980-0x02920 ===')
for insn in md.disasm(b[0x01980:0x02920],0x01980):
    if 0x01980 <= insn.address <= 0x02920:
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}')
print('=== function starts around strings/calls ===')
# find likely call to OperationSelect via t9 rel start, if call target could be local? Print lw t9 offsets at addresses 0x20e0-0x2188 and GOT values maybe not easy
