from pathlib import Path
import hashlib, struct, re, binascii
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
boot=ROOT/r'dumps\original\mtd1_bootloader.bin'
if not boot.exists():
    full=(ROOT/r'dumps\original\flash_full_mtd0.bin').read_bytes()
    boot.write_bytes(full[:0x30000])
b=boot.read_bytes()
print('BOOT', boot, 'size', len(b), 'sha256', hashlib.sha256(b).hexdigest().upper())
print('=== addiu/li immediate 0x1B candidates ===')
candidates=[]
for off in range(0, len(b)-4, 4):
    w=struct.unpack_from('<I', b, off)[0]
    if (w & 0xffff) == 0x001b and (w & 0xfc1f0000) == 0x24000000:
        rt=(w>>16)&31
        candidates.append((off,w,rt))
        print(f'0x{off:05X}: word=0x{w:08X} addiu r{rt},r0,0x1b')
print('count', len(candidates))
print('=== ori immediate 0x1B candidates ===')
for off in range(0, len(b)-4, 4):
    w=struct.unpack_from('<I', b, off)[0]
    if (w & 0xffff) == 0x001b and (w & 0xfc1f0000) == 0x34000000:
        rt=(w>>16)&31
        print(f'0x{off:05X}: word=0x{w:08X} ori r{rt},r0,0x1b')
print('=== contexts ===')
for off,w,rt in candidates:
    print(f'--- candidate 0x{off:05X} ---')
    start=max(0,off-0x40); end=min(len(b),off+0x80)
    for p in range(start,end,4):
        ww=struct.unpack_from('<I', b, p)[0]
        marker=' <==' if p==off else ''
        print(f'0x{p:05X}: {ww:08X}{marker}')
print('byte 0x1B count', b.count(b'\x1b'))
print('=== proposed simple patch candidates: replace low imm 0x1B -> 0x34 ===')
outdir=ROOT/r'dumps\modified'
outdir.mkdir(parents=True, exist_ok=True)
for idx,(off,w,rt) in enumerate(candidates):
    patched=bytearray(b)
    patched[off:off+2]=struct.pack('<H',0x0034)
    out=outdir/f'mtd1_bootloader_esc_to_4_candidate{idx}_off_{off:05X}.bin'
    out.write_bytes(patched)
    diffs=[i for i,(x,y) in enumerate(zip(b,patched)) if x!=y]
    print('CANDIDATE',idx,'offset',f'0x{off:05X}','diffs',[hex(d) for d in diffs],'sha256',hashlib.sha256(patched).hexdigest().upper(),'file',out)
print('=== source config hints ===')
for p in [ROOT/r'toolchain\uboot-mt7628-src\src\include\configs', ROOT/r'toolchain\uboot-mt7628-src\src']:
    print('DIR',p,'exists',p.exists())
    if p.exists():
        for q in list(p.glob('*7628*'))[:20]:
            print(q)
