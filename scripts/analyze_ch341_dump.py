from pathlib import Path
import hashlib, struct
cur = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\ch341\flash_full_ch341_20260917-211155.bin')
orig = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\original\flash_full_mtd0.bin')
mods = [Path(r'D:\PROJECTS\ENDOSCOPE\dumps\modified\mtd4_connectivity.bin'), Path(r'D:\PROJECTS\ENDOSCOPE\dumps\original\mtd4_kernel.bin')]

def sha(b): return hashlib.sha256(b).hexdigest().upper()
cb = cur.read_bytes(); ob = orig.read_bytes()
print('CURRENT', cur, len(cb), sha(cb))
print('ORIGINAL', orig, len(ob), sha(ob), 'match_full', cb==ob)
parts = [
    ('bootloader',0x00000,0x30000),
    ('config',0x30000,0x10000),
    ('factory',0x40000,0x10000),
    ('kernel/mtd4',0x50000,0x3B0000),
]
for name,off,size in parts:
    cs=cb[off:off+size]; os=ob[off:off+size]
    print('%-12s off=0x%06X size=0x%06X match=%s cur_sha=%s orig_sha=%s' % (name,off,size,cs==os,sha(cs),sha(os)))
    if cs!=os:
        for i,(a,b) in enumerate(zip(os,cs)):
            if a!=b:
                print('  first_mismatch absolute=0x%06X rel=0x%06X orig=%02X cur=%02X' % (off+i,i,a,b))
                break
# U-Boot image headers at mtd4 start
off=0x50000
h=cb[off:off+64]
print('mtd4_header_current', h.hex(' '))
magic=struct.unpack('>I', h[:4])[0]
if magic==0x27051956:
    fields=struct.unpack('>7I4B32s', h)
    print('uImage magic OK size=%d load=0x%08X entry=0x%08X name=%r' % (fields[3], fields[5], fields[6], fields[11].rstrip(b'\0')))
else:
    print('uImage magic not at mtd4 start: 0x%08X' % magic)
for m in mods:
    print('CHECK_FILE', m, 'exists', m.exists())
    if m.exists():
        mb=m.read_bytes()
        print('  size', len(mb), 'sha', sha(mb), 'matches_current_mtd4', mb==cb[0x50000:0x50000+len(mb)])
