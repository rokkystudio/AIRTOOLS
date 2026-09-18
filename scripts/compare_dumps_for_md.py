from pathlib import Path
import hashlib, struct, json, os
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
cur=ROOT/r'dumps\ch341\flash_full_ch341_20260917-211155.bin'
orig_full=ROOT/r'dumps\original\flash_full_mtd0.bin'
orig_mtd4=ROOT/r'dumps\original\mtd4_kernel.bin'
mod_mtd4=ROOT/r'dumps\modified\mtd4_connectivity.bin'
out_md=ROOT/r'dumps\ch341\flash_full_ch341_20260917-211155.compare.md'

def sha(p_or_b):
    b=p_or_b if isinstance(p_or_b,(bytes,bytearray)) else Path(p_or_b).read_bytes()
    return hashlib.sha256(b).hexdigest().upper()

def uimage_info(b):
    if len(b)<64: return {'valid':False,'reason':'too small'}
    magic,hcrc,timestamp,size,load,entry,dcrc = struct.unpack('>7I', b[:28])
    os_,arch,type_,comp = b[28],b[29],b[30],b[31]
    name=b[32:64].split(b'\0')[0].decode('ascii','replace')
    return dict(valid=(magic==0x27051956), magic=f'0x{magic:08X}', hcrc=f'0x{hcrc:08X}', timestamp=f'0x{timestamp:08X}', size=size, load=f'0x{load:08X}', entry=f'0x{entry:08X}', dcrc=f'0x{dcrc:08X}', os=os_, arch=arch, type=type_, comp=comp, name=name)

def first_mismatch(a,b,base=0):
    n=min(len(a),len(b))
    for i in range(n):
        if a[i]!=b[i]: return base+i,a[i],b[i]
    if len(a)!=len(b): return base+n,None,None
    return None

cb=cur.read_bytes(); ob=orig_full.read_bytes()
parts=[('mtd1_bootloader',0x00000,0x30000),('mtd2_config',0x30000,0x10000),('mtd3_factory',0x40000,0x10000),('mtd4_kernel',0x50000,0x3B0000)]
lines=[]
lines.append('# CH341 dump comparison\n')
lines.append(f'- Current dump: `{cur}`')
lines.append(f'- Current size: `{len(cb)}`')
lines.append(f'- Current SHA256: `{sha(cb)}`')
lines.append(f'- Original full dump: `{orig_full}`')
lines.append(f'- Original SHA256: `{sha(ob)}`')
lines.append(f'- Full match: `{cb==ob}`\n')
lines.append('## Partition comparison\n')
lines.append('| Partition | Offset | Size | Match original | Current SHA256 | Original SHA256 | First mismatch |')
lines.append('|---|---:|---:|---:|---|---|---|')
for name,off,size in parts:
    cs=cb[off:off+size]; os_=ob[off:off+size]
    mm=first_mismatch(os_,cs,off)
    mm_s='-' if mm is None else f'0x{mm[0]:06X}: orig={mm[1]:02X} cur={mm[2]:02X}'
    lines.append(f'| {name} | `0x{off:06X}` | `0x{size:06X}` | `{cs==os_}` | `{sha(cs)}` | `{sha(os_)}` | {mm_s} |')
lines.append('\n## mtd4 image header\n')
for label,b in [('current_mtd4', cb[0x50000:0x400000]), ('original_mtd4', orig_mtd4.read_bytes()), ('modified_mtd4', mod_mtd4.read_bytes())]:
    info=uimage_info(b)
    lines.append(f'### {label}')
    lines.append('')
    for k,v in info.items(): lines.append(f'- {k}: `{v}`')
    lines.append(f'- file/region SHA256: `{sha(b)}`')
    lines.append('')
lines.append('## Known files\n')
for p in [orig_full, orig_mtd4, mod_mtd4, cur]:
    lines.append(f'- `{p}` size=`{p.stat().st_size}` sha256=`{sha(p)}`')
out_md.write_text('\n'.join(lines), encoding='utf-8')
print(out_md)
print('\n'.join(lines[:80]))
