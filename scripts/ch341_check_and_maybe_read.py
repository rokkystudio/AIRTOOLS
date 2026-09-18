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

def is_jedec(b):
    return b.find(bytes([0xEF,0x40,0x16])) >= 0 or b.find(bytes([0xEF,0x40,0x15])) >= 0

h=dll.CH341OpenDevice(0)
ok=bool(h and h != wintypes.HANDLE(-1).value)
print('open_handle=%s ok=%s' % (h, ok))
if not ok:
    raise SystemExit(2)
found=None
try:
    for mode in (0x80,0x81,0x82,0x83):
        print('MODE 0x%02X set=%s' % (mode, bool(dll.CH341SetStream(0, mode))))
        for cs in (0,0x80,1,0x81):
            tests=[
                ('JEDEC_9F',[0x9F,0,0,0]),
                ('MFID_90',[0x90,0,0,0,0,0]),
                ('REMS_AB',[0xAB,0,0,0,0]),
                ('RDSR_05',[0x05,0]),
            ]
            for name,data in tests:
                r,b=xfer(cs,data)
                print('cs=0x%02X %-8s ok=%s data=%s' % (cs,name,r,b.hex(' ')))
                if name == 'JEDEC_9F' and is_jedec(b):
                    found=(mode,cs,b)
    if not found:
        print('NO_VALID_JEDEC')
    else:
        mode,cs,j=found
        print('VALID_JEDEC mode=0x%02X cs=0x%02X data=%s' % (mode,cs,j.hex(' ')))
        # Read first 256 bytes, then whole 4MiB if header looks non-floating.
        dll.CH341SetStream(0, mode)
        def read_flash(addr, n, cs=cs):
            data=bytearray()
            pos=0
            while pos<n:
                chunk=min(4096,n-pos)
                a=addr+pos
                tx=[0x03,(a>>16)&255,(a>>8)&255,a&255]+[0]*chunk
                r,b=xfer(cs,tx)
                if not r:
                    raise RuntimeError('SPI read failed at 0x%06X' % a)
                data.extend(b[4:])
                pos+=chunk
            return bytes(data)
        first=read_flash(0,256)
        print('FIRST256_SHA256', hashlib.sha256(first).hexdigest().upper())
        print('FIRST256_HEX', first[:64].hex(' '))
        if first.count(0xff) == len(first) or first.count(0x00) == len(first):
            print('FIRST256_FLOATING_OR_EMPTY_SKIP_FULL_READ')
        else:
            outdir=Path(r'D:\PROJECTS\ENDOSCOPE\dumps\ch341')
            outdir.mkdir(parents=True, exist_ok=True)
            ts=time.strftime('%Y%m%d-%H%M%S')
            out=outdir/(f'flash_full_ch341_{ts}.bin')
            size=4*1024*1024
            print('READ_FULL_START', out)
            sha=hashlib.sha256()
            with out.open('wb') as f:
                for off in range(0,size,4096):
                    d=read_flash(off,4096)
                    f.write(d); sha.update(d)
                    if off % (256*1024)==0:
                        print('READ_OFF 0x%06X' % off, flush=True)
            print('READ_FULL_DONE path=%s size=%d sha256=%s' % (out, out.stat().st_size, sha.hexdigest().upper()))
            orig=Path(r'D:\PROJECTS\ENDOSCOPE\dumps\original\flash_full_mtd0.bin')
            if orig.exists():
                ob=orig.read_bytes()
                nb=out.read_bytes()
                print('ORIG_SIZE', len(ob), 'NEW_SIZE', len(nb))
                print('MATCH_ORIGINAL', ob == nb)
finally:
    dll.CH341CloseDevice(0)
    print('closed')
