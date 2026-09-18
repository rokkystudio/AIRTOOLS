from pathlib import Path
import struct, re, collections
from capstone import Cs, CS_ARCH_MIPS, CS_MODE_MIPS32, CS_MODE_LITTLE_ENDIAN
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
b=(ROOT/r'dumps\original\mtd1_bootloader.bin').read_bytes()
# relevant string offsets from previous scan
rel=[
('Please choose',0x12D65),('Load system',0x12D84),('Boot default',0x12DEC),('BootType',0x1324C),('default fmt',0x13258),('System Boot',0x13274),('Enter CLI',0x1336C),('System Boot Linux via Flash',0x135A8),('MT7628 prompt',0x149E4)]
# Decode addiu/ori a0,a0/zero immediates and find common base hypothesis string_off - imm
refs=[]
for off in range(0,len(b)-4,4):
    w=struct.unpack_from('<I',b,off)[0]
    op=(w>>26)&0x3f; rs=(w>>21)&31; rt=(w>>16)&31; imm=w&0xffff
    simm=imm if imm<0x8000 else imm-0x10000
    # addiu rt,rs,imm or ori
    if op in (0x09,0x0d) and rt==4:  # writes a0
        refs.append((off,w,op,rs,rt,simm,imm))
print('refs writing a0 count',len(refs))
base_hits=collections.defaultdict(list)
for name,soff in rel:
    for off,w,op,rs,rt,simm,imm in refs:
        # Usually imm positive offset within string region
        base=soff - simm
        if 0 <= base <= len(b):
            # accept bases that repeat and are aligned-ish
            base_hits[base].append((name,soff,off,w,op,rs,simm))
print('=== common base hypotheses ===')
for base,hits in sorted(base_hits.items(), key=lambda kv:-len(kv[1]))[:20]:
    if len(hits)>=2:
        print(f'BASE 0x{base:05X} hits {len(hits)}')
        for h in hits[:20]:
            name,soff,off,w,op,rs,simm=h
            opname='addiu' if op==0x09 else 'ori'
            print(f'  str {name:20s} 0x{soff:05X} code 0x{off:05X} {opname} a0,r{rs},0x{simm&0xffff:04X}')
# Based on best bases, disasm around code refs to default/System Boot
print('=== refs for default/System Boot strings likely ===')
for base,hits in sorted(base_hits.items(), key=lambda kv:-len(kv[1]))[:5]:
    if len(hits)>=2:
        for name,soff,off,w,op,rs,simm in hits:
            if name in ('default fmt','System Boot','BootType','Enter CLI','System Boot Linux via Flash'):
                print('REF',name,'string',hex(soff),'base',hex(base),'code',hex(off))
                start=max(0, off-0x120); end=min(len(b), off+0x220)
                md=Cs(CS_ARCH_MIPS, CS_MODE_MIPS32|CS_MODE_LITTLE_ENDIAN)
                for insn in md.disasm(b[start:end], start):
                    mark=' <REF>' if insn.address==off else ''
                    print(f'0x{insn.address:05X}: {insn.bytes.hex():11s} {insn.mnemonic:8s} {insn.op_str}{mark}')
                print('---')
