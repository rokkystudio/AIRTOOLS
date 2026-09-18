import ctypes, hashlib, time
from ctypes import wintypes
from pathlib import Path

dll = ctypes.WinDLL(r'C:\Windows\System32\CH341DLLA64.DLL')
dll.CH341OpenDevice.argtypes=[wintypes.ULONG]
dll.CH341OpenDevice.restype=wintypes.HANDLE
dll.CH341CloseDevice.argtypes=[wintypes.ULONG]
dll.CH341CloseDevice.restype=None
dll.CH341SetStream.argtypes=[wintypes.ULONG,wintypes.ULONG]
dll.CH341SetStream.restype=wintypes.BOOL
dll.CH341StreamSPI4.argtypes=[wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p]
dll.CH341StreamSPI4.restype=wintypes.BOOL

def xfer(cs, data):
    arr=(ctypes.c_ubyte*len(data))(*data)
    ok=dll.CH341StreamSPI4(0, cs, len(data), ctypes.byref(arr))
    return bool(ok), bytes(arr)

h=dll.CH341OpenDevice(0)
ok=bool(h and h != wintypes.HANDLE(-1).value)
print('open_handle=%s ok=%s' % (h, ok), flush=True)
if not ok:
    raise SystemExit(2)
try:
    # Known working combination from last run.
    mode=0x83
    cs=0x80
    print('set_stream 0x%02X = %s' % (mode, bool(dll.CH341SetStream(0, mode))), flush=True)
    for i in range(3):
        r,j=xfer(cs,[0x9F,0,0,0])
        print('JEDEC_try%d ok=%s data=%s' % (i,r,j.hex(' ')), flush=True)
    r,j=xfer(cs,[0x9F,0,0,0])
    if bytes([0xEF,0x40,0x16]) not in j:
        print('NO_VALID_JEDEC_ABORT', flush=True)
        raise SystemExit(4)

    def read_flash(addr, n, chunk=252):
        data=bytearray()
        pos=0
        while pos<n:
            ln=min(chunk,n-pos)
            a=addr+pos
            tx=[0x03,(a>>16)&255,(a>>8)&255,a&255]+[0]*ln
            r,b=xfer(cs,tx)
            if not r:
                raise RuntimeError('SPI read failed at 0x%06X len=%d' % (a, ln))
            data.extend(b[4:4+ln])
            pos += ln
        return bytes(data)

    first=read_flash(0,256,chunk=64)
    print('FIRST256_SHA256', hashlib.sha256(first).hexdigest().upper(), flush=True)
    print('FIRST64_HEX', first[:64].hex(' '), flush=True)
    orig=Path(r'D:\PROJECTS\ENDOSCOPE\dumps\original\flash_full_mtd0.bin')
    if orig.exists():
        ob=orig.read_bytes()[:256]
        print('FIRST256_MATCH_ORIG', first==ob, flush=True)
        print('ORIG_FIRST64_HEX', ob[:64].hex(' '), flush=True)

    outdir=Path(r'D:\PROJECTS\ENDOSCOPE\dumps\ch341')
    outdir.mkdir(parents=True, exist_ok=True)
    ts=time.strftime('%Y%m%d-%H%M%S')
    out=outdir/(f'flash_full_ch341_{ts}.bin')
    size=4*1024*1024
    print('READ_FULL_START', out, flush=True)
    sha=hashlib.sha256()
    with out.open('wb') as f:
        for off in range(0,size,256):
            d=read_flash(off,256,chunk=252)
            f.write(d); sha.update(d)
            if off % (256*1024)==0:
                print('READ_OFF 0x%06X' % off, flush=True)
    print('READ_FULL_DONE path=%s size=%d sha256=%s' % (out, out.stat().st_size, sha.hexdigest().upper()), flush=True)
    if orig.exists():
        nb=out.read_bytes()
        ob=orig.read_bytes()
        print('ORIG_SIZE', len(ob), 'NEW_SIZE', len(nb), flush=True)
        print('MATCH_ORIGINAL', ob==nb, flush=True)
        # Count first mismatch if any
        if ob!=nb:
            for i,(a,b) in enumerate(zip(ob,nb)):
                if a!=b:
                    print('FIRST_MISMATCH 0x%06X orig=%02X new=%02X' % (i,a,b), flush=True)
                    break
finally:
    dll.CH341CloseDevice(0)
    print('closed', flush=True)
