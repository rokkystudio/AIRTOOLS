from pathlib import Path
import struct, hashlib
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32 | CS_MODE_LITTLE_ENDIAN)
# use file offset as address for readability
cands=[0x06948,0x0BD2C,0x10104,0x071A0,0x0A1A4]
for c in cands:
    start=max(0,c-0x80); end=min(len(b), c+0x100)
    print(f'=== DISASM around 0x{c:05X} ===')
    for insn in md.disasm(b[start:end], start):
        mark=' <==' if insn.address==c else ''
        print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}{mark}')
# scan for jal getc? Need identify calls around 0xBD2C maybe by branch/call pattern.
# Also compare patched disasm of 0xBD2C 0x1b -> 0x34
patched=bytearray(b)
patched[0x0BD2C:0x0BD2E]=struct.pack('<H',0x0034)
out=ROOT/r'dumps\modified\mtd1_bootloader_rescue_4_trigger_off_0BD2C.bin'
out.write_bytes(patched)
print('PATCH_FILE', out)
print('PATCH_SIZE', len(patched))
print('PATCH_SHA256', hashlib.sha256(patched).hexdigest().upper())
print('DIFFS')
for i,(x,y) in enumerate(zip(b,patched)):
    if x!=y:
        print(f'0x{i:05X}: {x:02X}->{y:02X}')
print('=== PATCHED DISASM around 0x0BD2C ===')
for insn in md.disasm(bytes(patched[0x0BD00:0x0BD80]), 0x0BD00):
    mark=' <==' if insn.address==0x0BD2C else ''
    print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}{mark}')
