from pathlib import Path
import ctypes, hashlib, time, sys
from ctypes import wintypes

ROOT=Path(r'D:\PROJECTS\AIRTOOLS')
IMG=ROOT/r'dumps\original\mtd1_bootloader.bin'
OUTDIR=ROOT/r'dumps\ch341_direct_restore_original'
OUTDIR.mkdir(parents=True, exist_ok=True)
OFFSET=0x000000
SIZE=0x030000
ERASE_BLOCK=0x10000
MODE=0x83
CS=0x80
EXPECTED_SHA='9012c77628e5a7724d7fea2641399978089445cfc655671ee872741725ca31b6'
img=IMG.read_bytes()
print('DIRECT_CH341_RESTORE_ORIGINAL_MTD1', flush=True)
print('IMAGE', IMG, 'size', len(img), 'sha256', hashlib.sha256(img).hexdigest(), flush=True)
if len(img)!=SIZE:
    raise SystemExit('BAD_IMAGE_SIZE')
if hashlib.sha256(img).hexdigest()!=EXPECTED_SHA:
    raise SystemExit('BAD_IMAGE_SHA')

dll=ctypes.WinDLL(r'C:\Windows\System32\CH341DLLA64.DLL')
dll.CH341OpenDevice.argtypes=[wintypes.ULONG]
dll.CH341OpenDevice.restype=wintypes.HANDLE
dll.CH341CloseDevice.argtypes=[wintypes.ULONG]
dll.CH341CloseDevice.restype=None
dll.CH341SetStream.argtypes=[wintypes.ULONG,wintypes.ULONG]
dll.CH341SetStream.restype=wintypes.BOOL
dll.CH341StreamSPI4.argtypes=[wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p]
dll.CH341StreamSPI4.restype=wintypes.BOOL

def xfer(data,label=''):
    arr=(ctypes.c_ubyte*len(data))(*data)
    ok=dll.CH341StreamSPI4(0,CS,len(data),ctypes.byref(arr))
    if not ok:
        raise RuntimeError('CH341StreamSPI4 failed '+label+' '+bytes(data[:8]).hex(' '))
    return bytes(arr)

def rdsr():
    return xfer([0x05,0x00],'RDSR')[1]

def wait_ready(label, timeout_s=120.0):
    start=time.time()
    last=None
    while True:
        sr=rdsr(); last=sr
        if (sr & 1)==0:
            return sr
        if time.time()-start>timeout_s:
            raise TimeoutError(f'wait_ready timeout {label} sr=0x{last:02X}')
        time.sleep(0.02)

def wren():
    xfer([0x06],'WREN')
    time.sleep(0.005)
    sr=rdsr()
    if (sr & 2)==0:
        print('WARN_WEL_NOT_SET sr=0x%02X continuing' % sr, flush=True)
    return sr

def wrdi():
    try:
        xfer([0x04],'WRDI')
        time.sleep(0.005)
    except Exception as e:
        print('WARN_WRDI',repr(e),flush=True)

def read_flash(addr,n,chunk=252):
    out=bytearray(); pos=0
    while pos<n:
        ln=min(chunk,n-pos); a=addr+pos
        rx=xfer([0x03,(a>>16)&255,(a>>8)&255,a&255]+[0]*ln,'READ')
        out.extend(rx[4:4+ln]); pos+=ln
    return bytes(out)

def erase64(addr):
    print('ERASE64_START',f'0x{addr:06X}',flush=True)
    wren()
    xfer([0xD8,(addr>>16)&255,(addr>>8)&255,addr&255],'ERASE64')
    sr=wait_ready('erase 0x%06X'%addr,180.0)
    print('ERASE64_DONE',f'0x{addr:06X}','sr=0x%02X'%sr,flush=True)

def page_program(addr,page):
    wren()
    xfer([0x02,(addr>>16)&255,(addr>>8)&255,addr&255]+list(page),'PP')
    wait_ready('program 0x%06X'%addr,10.0)

h=dll.CH341OpenDevice(0)
ok=bool(h and h != wintypes.HANDLE(-1).value)
print('OPEN',h,ok,flush=True)
if not ok:
    raise SystemExit('CH341_OPEN_FAILED')
try:
    print('SET_STREAM',hex(MODE),bool(dll.CH341SetStream(0,MODE)),flush=True)
    for i in range(5):
        jedec=xfer([0x9F,0,0,0],'JEDEC')
        sr=xfer([0x05,0],'RDSR')
        print('ID_%d'%i,'JEDEC',jedec.hex(' '),'SR',sr.hex(' '),flush=True)
    ts=time.strftime('%Y%m%d-%H%M%S')
    try:
        pre=read_flash(OFFSET,SIZE)
        p=OUTDIR/f'mtd1_before_direct_restore_{ts}.bin'
        p.write_bytes(pre)
        print('BEFORE_READ',p,len(pre),hashlib.sha256(pre).hexdigest(),'ff_count',pre.count(0xff),flush=True)
    except Exception as e:
        print('WARN_BEFORE_READ_FAILED',repr(e),flush=True)

    print('WRITE_ORIGINAL_MTD1_START offset=0x000000 size=0x030000',flush=True)
    for addr in range(OFFSET, OFFSET+SIZE, ERASE_BLOCK):
        erase64(addr)
    print('ERASE_ALL_DONE',flush=True)

    for off in range(0,SIZE,256):
        page_program(OFFSET+off,img[off:off+256])
        if off % 0x2000 == 0:
            print('PROGRAM_OFF',f'0x{off:06X}',flush=True)
    print('PROGRAM_ALL_DONE',flush=True)

    rb=read_flash(OFFSET,SIZE)
    rb_path=OUTDIR/f'mtd1_after_direct_restore_{ts}.bin'
    rb_path.write_bytes(rb)
    rb_sha=hashlib.sha256(rb).hexdigest()
    print('AFTER_READ',rb_path,len(rb),rb_sha,'ff_count',rb.count(0xff),flush=True)
    print('MATCH_ORIGINAL',rb==img,flush=True)
    if rb!=img:
        first=None
        for i,(a,b) in enumerate(zip(img,rb)):
            if a!=b:
                first=i; break
        print('FIRST_MISMATCH',hex(first) if first is not None else 'none', 'orig=%02X'%img[first] if first is not None else '', 'read=%02X'%rb[first] if first is not None else '', flush=True)
        raise SystemExit('VERIFY_FAILED')
    wrdi()
    print('DIRECT_RESTORE_ORIGINAL_MTD1_SUCCESS',flush=True)
finally:
    try: wrdi()
    except Exception: pass
    dll.CH341CloseDevice(0)
    print('CLOSED',flush=True)
