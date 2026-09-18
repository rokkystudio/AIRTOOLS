import ctypes, time
from ctypes import wintypes

def try_dll(path):
    print('DLL', path)
    dll = ctypes.WinDLL(path)
    dll.CH341OpenDevice.argtypes = [wintypes.ULONG]
    dll.CH341OpenDevice.restype = wintypes.HANDLE
    dll.CH341CloseDevice.argtypes = [wintypes.ULONG]
    dll.CH341CloseDevice.restype = None
    dll.CH341SetStream.argtypes = [wintypes.ULONG, wintypes.ULONG]
    dll.CH341SetStream.restype = wintypes.BOOL
    dll.CH341StreamSPI4.argtypes = [wintypes.ULONG, wintypes.ULONG, wintypes.ULONG, ctypes.c_void_p]
    dll.CH341StreamSPI4.restype = wintypes.BOOL
    try:
        dll.CH341GetVersion.restype = wintypes.ULONG
        print(' version=0x%08X' % dll.CH341GetVersion())
    except Exception as e:
        print(' version_err', e)
    opened = False
    for idx in range(16):
        h = dll.CH341OpenDevice(idx)
        ok = bool(h and h != wintypes.HANDLE(-1).value)
        print(' idx=%d handle=%s ok=%s' % (idx, h, ok))
        if ok:
            opened = True
            try:
                for mode in (0x80, 0x81, 0x82, 0x83):
                    print('  set_stream 0x%02X = %s' % (mode, bool(dll.CH341SetStream(idx, mode))))
                    for cs in (0, 0x80, 1, 0x81):
                        buf = (ctypes.c_ubyte * 4)(0x9F, 0, 0, 0)
                        r = dll.CH341StreamSPI4(idx, cs, 4, ctypes.byref(buf))
                        print('   cs=0x%02X ok=%s data=%s' % (cs, bool(r), bytes(buf).hex(' ')))
            finally:
                dll.CH341CloseDevice(idx)
                print('  closed')
    return opened

opened = False
for p in [r'C:\Windows\System32\CH341DLLA64.DLL']:
    try:
        opened |= try_dll(p)
    except Exception as e:
        print('DLL_ERROR', p, repr(e))
print('OPENED_ANY=', opened)
