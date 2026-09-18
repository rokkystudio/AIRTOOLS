import ctypes
from ctypes import wintypes

dll = ctypes.WinDLL(r'C:\Windows\System32\CH341DLLA64.DLL')
for name in ['CH341OpenDevice','CH341OpenDeviceEx','CH341CloseDevice','CH341CloseDeviceEx','CH341SetExclusive']:
    try: getattr(dll, name); print('has', name)
    except Exception as e: print('no', name, e)

# Try common prototypes.
dll.CH341OpenDevice.argtypes=[wintypes.ULONG]
dll.CH341OpenDevice.restype=wintypes.HANDLE
dll.CH341CloseDevice.argtypes=[wintypes.ULONG]
dll.CH341CloseDevice.restype=None
try:
    dll.CH341SetExclusive.argtypes=[wintypes.ULONG, wintypes.BOOL]
    dll.CH341SetExclusive.restype=wintypes.BOOL
except Exception:
    pass

print('try CH341OpenDevice indexes')
for idx in range(0,16):
    h=dll.CH341OpenDevice(idx)
    ok = bool(h and h != wintypes.HANDLE(-1).value)
    print(idx, h, ok)
    if ok:
        try:
            print(' exclusive false', bool(dll.CH341SetExclusive(idx, False)))
        except Exception as e:
            print(' exclusive err', e)
        dll.CH341CloseDevice(idx)

print('try CH341OpenDeviceEx variants')
# Variant A: ULONG -> HANDLE
try:
    f=dll.CH341OpenDeviceEx
    f.argtypes=[wintypes.ULONG]
    f.restype=wintypes.HANDLE
    for idx in range(0,16):
        h=f(idx)
        ok=bool(h and h != wintypes.HANDLE(-1).value)
        print('A', idx, h, ok)
        if ok:
            try: dll.CH341CloseDevice(idx)
            except Exception: pass
except Exception as e:
    print('A error', repr(e))

# Variant B: no args -> HANDLE
try:
    f=dll.CH341OpenDeviceEx
    f.argtypes=[]
    f.restype=wintypes.HANDLE
    h=f()
    print('B noarg', h, bool(h and h != wintypes.HANDLE(-1).value))
except Exception as e:
    print('B error', repr(e))
