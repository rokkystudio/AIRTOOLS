from pathlib import Path
import hashlib, struct, binascii, time
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
files={
    'stock_mtd4': ROOT/r'dumps\original\mtd4_kernel.bin',
    'patch_mtd4': ROOT/r'dumps\modified\mtd4_connectivity.bin',
    'bad_read_mtd4_current_before_restore': ROOT/r'dumps\ch341\flash_full_ch341_20260917-211155.bin',
}

IH_MAGIC=0x27051956
IH_OS_LINUX=5
IH_ARCH_MIPS=5
IH_TYPE_KERNEL=2
IH_COMP_LZMA=3

def sha(p):
    b=p.read_bytes(); return len(b), hashlib.sha256(b).hexdigest().upper(), b

def parse_uimage(data):
    if len(data)<64: return {'ok':False,'err':'too short'}
    fields=struct.unpack('>7I4B32s', data[:64])
    magic,hcrc,ts,size,load,entry,dcrc,os,arch,typ,comp,name=fields
    hdr=bytearray(data[:64]); hdr[4:8]=b'\0\0\0\0'
    calc_h=binascii.crc32(hdr)&0xffffffff
    payload=data[64:64+size]
    calc_d=binascii.crc32(payload)&0xffffffff if len(payload)==size else None
    return {
        'magic': magic, 'hcrc': hcrc, 'hcrc_calc': calc_h, 'hcrc_ok': hcrc==calc_h,
        'timestamp': ts, 'size': size, 'load': load, 'entry': entry, 'dcrc': dcrc, 'dcrc_calc': calc_d,
        'dcrc_ok': calc_d==dcrc if calc_d is not None else False,
        'payload_available': len(payload), 'os':os, 'arch':arch, 'type':typ, 'comp':comp,
        'name': name.rstrip(b'\0').decode('ascii','replace'),
        'known_ok': magic==IH_MAGIC and os==IH_OS_LINUX and arch==IH_ARCH_MIPS and typ==IH_TYPE_KERNEL and comp==IH_COMP_LZMA and hcrc==calc_h and calc_d==dcrc
    }

print('=== PATCH PREFLIGHT READ-ONLY ===')
stock_len, stock_sha, stock = sha(files['stock_mtd4'])
patch_len, patch_sha, patch = sha(files['patch_mtd4'])
print('STOCK', files['stock_mtd4'], stock_len, stock_sha)
print('PATCH', files['patch_mtd4'], patch_len, patch_sha)
print('SIZE_OK', patch_len == 0x3B0000)
print('PATCH_EQUALS_STOCK', patch == stock)

for label,data in [('stock',stock),('patch',patch)]:
    u=parse_uimage(data)
    print(f'--- UIMAGE {label} ---')
    for k in ['magic','hcrc','hcrc_calc','hcrc_ok','size','load','entry','dcrc','dcrc_calc','dcrc_ok','os','arch','type','comp','name','known_ok']:
        v=u.get(k)
        if isinstance(v,int):
            if k in ('magic','hcrc','hcrc_calc','load','entry','dcrc','dcrc_calc'):
                print(k, f'0x{v:08X}')
            else:
                print(k, v)
        else:
            print(k, v)

# compare patch with bad mtd4 from full dump, if available
bad_full=files['bad_read_mtd4_current_before_restore']
if bad_full.exists():
    bf=bad_full.read_bytes()
    bad=bf[0x50000:0x400000]
    print('BAD_MTD4_SHA_FROM_BEFORE_RESTORE', hashlib.sha256(bad).hexdigest().upper())
    print('PATCH_EQUALS_BAD_PREVIOUS', patch == bad)
    # first mismatch to stock, patch, bad
    def firstdiff(a,b):
        for i,(x,y) in enumerate(zip(a,b)):
            if x!=y: return i,x,y
        return None
    print('FIRST_DIFF_STOCK_PATCH', firstdiff(stock,patch))
    print('FIRST_DIFF_PATCH_BAD', firstdiff(patch,bad))

# create report md
report=ROOT/r'dumps\modified\mtd4_connectivity.preflight.md'
lines=[]
lines.append('# mtd4 connectivity patch preflight')
lines.append('')
lines.append(f'- generated: {time.strftime("%Y-%m-%d %H:%M:%S")}')
lines.append(f'- stock: `{files["stock_mtd4"]}`')
lines.append(f'- stock size/SHA256: `{stock_len}` / `{stock_sha}`')
lines.append(f'- patch: `{files["patch_mtd4"]}`')
lines.append(f'- patch size/SHA256: `{patch_len}` / `{patch_sha}`')
lines.append(f'- size ok 0x3B0000: `{patch_len == 0x3B0000}`')
lines.append(f'- patch equals stock: `{patch == stock}`')
for label,data in [('stock',stock),('patch',patch)]:
    u=parse_uimage(data)
    lines.append('')
    lines.append(f'## uImage {label}')
    for k in ['magic','hcrc','hcrc_calc','hcrc_ok','size','load','entry','dcrc','dcrc_calc','dcrc_ok','os','arch','type','comp','name','known_ok']:
        v=u.get(k)
        if isinstance(v,int) and k in ('magic','hcrc','hcrc_calc','load','entry','dcrc','dcrc_calc'):
            v=f'0x{v:08X}'
        lines.append(f'- {k}: `{v}`')
report.write_text('\n'.join(lines)+'\n', encoding='utf-8')
print('REPORT', report)
