from pathlib import Path
import ctypes, hashlib, time
from ctypes import wintypes

ROOT=Path(r'D:\PROJECTS\AIRTOOLS')
ORIG=ROOT/r'dumps\original\mtd1_bootloader.bin'
OUTDIR=ROOT/r'dumps\ch341_readonly_checks'
OUTDIR.mkdir(parents=True, exist_ok=True)
orig=ORIG.read_bytes()
print('READONLY_CHECK_ONLY_NO_WRITE_COMMANDS', flush=True)
print('ORIG', ORIG, len(orig), hashlib.sha256(orig).hexdigest(), flush=True)

DLL=r'C:\Windows\System32\CH341DLLA64.DLL'
dll=ctypes.WinDLL(DLL)
dll.CH341OpenDevice.argtypes=[wintypes.ULONG]; dll.CH341OpenDevice.restype=wintypes.HANDLE
dll.CH341CloseDevice.argtypes=[wintypes.ULONG]; dll.CH341CloseDevice.restype=None
dll.CH341SetStream.argtypes=[wintypes.ULONG,wintypes.ULONG]; dll.CH341SetStream.restype=wintypes.BOOL
dll.CH341StreamSPI4.argtypes=[wintypes.ULONG,wintypes.ULONG,wintypes.ULONG,ctypes.c_void_p]; dll.CH341StreamSPI4.restype=wintypes.BOOL

def xfer(data,cs):
    # READ-ONLY commands only: 0x9F,0x05,0x90,0xAB,0x03 are used by caller.
    arr=(ctypes.c_ubyte*len(data))(*data)
    ok=dll.CH341StreamSPI4(0,cs,len(data),ctypes.byref(arr))
    if not ok:
        print('XFER_FALSE', bytes(data[:8]).hex(' '), 'cs', hex(cs), flush=True)
    return bool(ok), bytes(arr)

def read_flash(cs,addr,n,chunk=252):
    out=bytearray(); pos=0
    while pos<n:
        ln=min(chunk,n-pos); a=addr+pos
        ok,b=xfer([0x03,(a>>16)&255,(a>>8)&255,a&255]+[0]*ln,cs)
        out.extend(b[4:4+ln]); pos+=ln
    return bytes(out)

def summarize(tag,d):
    sha=hashlib.sha256(d).hexdigest()
    print(tag,'size',len(d),'sha256',sha,flush=True)
    print(tag,'first64',d[:64].hex(' '),flush=True)
    print(tag,'counts_ff_00',d.count(0xff),d.count(0x00),flush=True)
    print(tag,'match_original',d==orig,flush=True)
    if d!=orig and len(d)==len(orig):
        first=last=None; cnt=0
        for i,(a,b) in enumerate(zip(orig,d)):
            if a!=b:
                cnt+=1
                if first is None: first=i
                last=i
        print(tag,'diff_count',cnt,'first',hex(first) if first is not None else 'none','last',hex(last) if last is not None else 'none',flush=True)
        for block in range(0,len(orig),0x10000):
            o=orig[block:block+0x10000]; r=d[block:block+0x10000]
            bd=sum(1 for a,b in zip(o,r) if a!=b)
            print(tag,'block',hex(block),'diff',bd,'ff',r.count(0xff),'sha',hashlib.sha256(r).hexdigest(),flush=True)
        for off in [0,0x390,0x21ac,0x10000,0x16b14,0x20000,0x2ff00]:
            print(tag,'off',hex(off),'orig',orig[off:off+16].hex(' '),'read',d[off:off+16].hex(' '),flush=True)
    return sha

h=dll.CH341OpenDevice(0)
ok=bool(h and h != wintypes.HANDLE(-1).value)
print('OPEN',h,ok,flush=True)
if not ok:
    raise SystemExit('OPEN_FAILED')
try:
    modes=[0x83,0x82,0x81,0x80,0x8f]
    cs_list=[0x80,0x00,0x81,0x01]
    print('ID_SWEEP_READ_ONLY', flush=True)
    candidates=[]
    for mode in modes:
        print('\nMODE',hex(mode),'set',bool(dll.CH341SetStream(0,mode)),flush=True)
        for cs in cs_list:
            vals=[]
            for name,cmd in [('9F',[0x9F,0,0,0]),('05',[0x05,0]),('90',[0x90,0,0,0,0,0]),('AB',[0xAB,0,0,0,0])]:
                ok,b=xfer(cmd,cs); vals.append((name,b))
            read4=read_flash(cs,0,4,4)
            print(' cs',hex(cs),' '.join(f'{n}={b.hex(" ")}' for n,b in vals),'READ4='+read4.hex(' '),flush=True)
            if any(bytes([0xEF,0x40,0x16]) in b for _,b in vals) or read4 != b'\xff'*4:
                candidates.append((mode,cs))
    # Always include known tuple first, then candidates.
    todo=[]
    for t in [(0x83,0x80),(0x82,0x80),(0x81,0x80),(0x80,0x80),(0x8f,0x80)]+candidates:
        if t not in todo:
            todo.append(t)
    print('\nREADBACK_TUPLES',todo,flush=True)
    ts=time.strftime('%Y%m%d-%H%M%S')
    readbacks=[]
    for mode,cs in todo:
        print('\nREAD_MTD1',hex(mode),hex(cs),flush=True)
        dll.CH341SetStream(0,mode)
        d=read_flash(cs,0,0x30000)
        p=OUTDIR/f'mtd1_readonly_{ts}_mode{mode:02x}_cs{cs:02x}.bin'
        p.write_bytes(d)
        sha=summarize(str(p),d)
        readbacks.append((mode,cs,p,sha,d))
    print('\nREADBACK_CROSS_COMPARE',flush=True)
    for i in range(len(readbacks)):
        for j in range(i+1,len(readbacks)):
            same=readbacks[i][4]==readbacks[j][4]
            print('same',hex(readbacks[i][0]),hex(readbacks[i][1]),'vs',hex(readbacks[j][0]),hex(readbacks[j][1]),same,flush=True)
finally:
    # No write-disable command either, to stay strictly read-only.
    dll.CH341CloseDevice(0)
    print('CLOSED',flush=True)
