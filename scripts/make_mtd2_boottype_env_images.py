from pathlib import Path
import hashlib, binascii, struct, re
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
cur=sorted((ROOT/'dumps/current').glob('mtd2_config_flashr_*.bin'), key=lambda p:p.stat().st_mtime)[-1]
b=bytearray(cur.read_bytes())
assert len(b)==0x10000
assert all(x==0xff for x in b[:0x1000])
print('CURRENT',cur,'sha256',hashlib.sha256(b).hexdigest().upper())
outdir=ROOT/'dumps/modified'; outdir.mkdir(parents=True, exist_ok=True)

def make_env(boottype):
    # U-Boot env_t: uint32 crc + data[CFG_ENV_SIZE-4], CRC32 over data only.
    data=bytearray([0xff])*(0x1000-4)
    entries=[
        f'bootdelay=5',
        f'BootType={boottype}',
        # harmless defaults useful inside U-Boot CLI/TFTP
        'ipaddr=192.168.10.123',
        'serverip=192.168.10.36',
        'bootfile=uImage',
        'loadaddr=0x80100000',
        'baudrate=57600',
    ]
    blob=b'\x00'.join(e.encode('ascii') for e in entries)+b'\x00\x00'
    assert len(blob) < len(data)
    data[:len(blob)] = blob
    crc=binascii.crc32(data)&0xffffffff
    env=struct.pack('<I',crc)+data
    # verify
    assert (binascii.crc32(env[4:])&0xffffffff)==struct.unpack_from('<I',env,0)[0]
    return env, entries, crc
for bt in ['4','3']:
    img=bytearray(b)
    env, entries, crc = make_env(bt)
    img[:0x1000]=env
    name=outdir/f'mtd2_config_BootType{bt}_full_preserve_config.bin'
    name.write_bytes(img)
    print('OUT',name)
    print(' size',len(img),'sha256',hashlib.sha256(img).hexdigest().upper(),'crc',f'{crc:08X}')
    print(' first_non_ff', next((i for i,x in enumerate(img) if x!=0xff), None))
    print(' config_unchanged_from_0x2000', img[0x2000:]==b[0x2000:])
    print(' env_entries', entries)
    print(' env_head', img[:160].hex(' '))
# Compare diffs for BootType4 vs current
p=outdir/'mtd2_config_BootType4_full_preserve_config.bin'
img=p.read_bytes()
diff=[i for i,(x,y) in enumerate(zip(b,img)) if x!=y]
print('DIFF_COUNT_TO_CURRENT_BT4',len(diff),'first',hex(diff[0]),'last',hex(diff[-1]))
print('DIFF_RANGE_EXPECTED 0x0000..0x0fff only', max(diff)<0x1000)
