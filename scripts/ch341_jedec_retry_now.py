import ctypes
from ctypes import wintypes

dll = ctypes.WinDLL(r'C:\Windows\System32\CH341DLLA64.DLL')
dll.CH341OpenDevice.argtypes = [wintypes.ULONG]
dll.CH341OpenDevice.restype = wintypes.HANDLE
dll.CH341CloseDevice.argtypes = [wintypes.ULONG]
dll.CH341CloseDevice.restype = None
dll.CH341SetStream.argtypes = [wintypes.ULONG, wintypes.ULONG]
dll.CH341SetStream.restype = wintypes.BOOL
dll.CH341StreamSPI4.argtypes = [wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p]
dll.CH341StreamSPI4.restype = wintypes.BOOL

h = dll.CH341OpenDevice(0)
ok = bool(h and h != wintypes.HANDLE(-1).value)
print('open_handle=%s ok=%s' % (h, ok))
if not ok:
    raise SystemExit(2)
try:
    for mode in (0x80, 0x81, 0x82, 0x83):
        print('set_stream 0x%02X = %s' % (mode, bool(dll.CH341SetStream(0, mode))))
        for cs in (0, 0x80, 1, 0x81):
            buf = (ctypes.c_ubyte * 4)(0x9F, 0, 0, 0)
            r = dll.CH341StreamSPI4(0, cs, 4, ctypes.byref(buf))
            print('cs=0x%02X ok=%s data=%s' % (cs, bool(r), bytes(buf).hex(' ')))
finally:
    dll.CH341CloseDevice(0)
    print('closed')
