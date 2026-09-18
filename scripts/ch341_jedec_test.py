import ctypes, sys, time
from ctypes import wintypes

dll = ctypes.WinDLL(r'C:\Windows\System32\CH341DLLA64.DLL')

dll.CH341OpenDevice.argtypes = [wintypes.ULONG]
dll.CH341OpenDevice.restype = wintypes.HANDLE
dll.CH341CloseDevice.argtypes = [wintypes.ULONG]
dll.CH341CloseDevice.restype = None
dll.CH341GetVersion.argtypes = []
dll.CH341GetVersion.restype = wintypes.ULONG
dll.CH341GetDrvVersion.argtypes = []
dll.CH341GetDrvVersion.restype = wintypes.ULONG
dll.CH341SetStream.argtypes = [wintypes.ULONG, wintypes.ULONG]
dll.CH341SetStream.restype = wintypes.BOOL
dll.CH341StreamSPI4.argtypes = [wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p]
dll.CH341StreamSPI4.restype = wintypes.BOOL

idx = 0
print('dll_version=0x%08X' % dll.CH341GetVersion())
print('drv_version=0x%08X' % dll.CH341GetDrvVersion())
h = dll.CH341OpenDevice(idx)
print('open_handle=', h)
if not h or h == wintypes.HANDLE(-1).value:
    raise SystemExit('open failed')
try:
    # 0x81 is commonly used for SPI mode + 20K/100K-ish stream speed on CH341.
    ok = dll.CH341SetStream(idx, 0x81)
    print('set_stream_0x81=', bool(ok))
    for cs in (0, 0x80, 1, 0x81):
        buf = (ctypes.c_ubyte * 4)(0x9F, 0, 0, 0)
        ok = dll.CH341StreamSPI4(idx, cs, 4, ctypes.byref(buf))
        data = bytes(buf)
        print('cs=0x%02X ok=%s data=%s' % (cs, bool(ok), data.hex(' ')))
finally:
    dll.CH341CloseDevice(idx)
    print('closed')
