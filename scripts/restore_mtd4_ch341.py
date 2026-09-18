from pathlib import Path
import ctypes, hashlib, time, sys
from ctypes import wintypes

ROOT = Path(r'D:\PROJECTS\ENDOSCOPE')
stock = ROOT / r'dumps\original\mtd4_kernel.bin'
expected_sha = '72904FD990D724D81CF2EBD3C1E812954C55422442D16CAB7C0E152FF3610C2D'
OFFSET = 0x50000
SIZE = 0x3B0000
END = OFFSET + SIZE
assert END == 0x400000

# Put U-Boot source back to production default. Keep recovery patch separately.
board = ROOT / r'toolchain\uboot-mt7628-src\src\lib_mips\board.c'
if board.exists():
    txt = board.read_text(encoding='utf-8', errors='replace')
    txt2 = txt.replace("unsigned char BootType='4', confirm=0; /* patched: default to CLI, not flash boot */", "unsigned char BootType='3', confirm=0;")
    txt2 = txt2.replace("BootType = '4'; /* patched: invalid menu input falls back to CLI */", "BootType = '3';")
    if txt2 != txt:
        board.write_text(txt2, encoding='utf-8')
        print('SOURCE_REVERTED_TO_PRODUCTION_DEFAULT_3', flush=True)
    else:
        print('SOURCE_ALREADY_PRODUCTION_OR_UNCHANGED', flush=True)

if not stock.exists():
    raise SystemExit(f'MISSING_STOCK_MTD4 {stock}')
img = stock.read_bytes()
sha = hashlib.sha256(img).hexdigest().upper()
print('STOCK_FILE', stock, flush=True)
print('STOCK_SIZE', len(img), flush=True)
print('STOCK_SHA256', sha, flush=True)
if len(img) != SIZE:
    raise SystemExit(f'BAD_STOCK_SIZE expected={SIZE} got={len(img)}')
if sha != expected_sha:
    raise SystemExit(f'BAD_STOCK_SHA expected={expected_sha} got={sha}')

# uImage sanity
if img[:4] != bytes.fromhex('27 05 19 56'):
    raise SystemExit('BAD_UIMAGE_MAGIC')
print('UIMAGE_MAGIC_OK', flush=True)

# CH341 setup
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

MODE = 0x83
CS = 0x80

def cmd(data):
    ok, b = xfer(CS, data)
    if not ok:
        raise RuntimeError('SPI command failed: ' + bytes(data).hex(' '))
    return b

def rdsr():
    b = cmd([0x05, 0x00])
    return b[1]

def wait_ready(label, timeout_s=20.0):
    start = time.time()
    while True:
        sr = rdsr()
        if (sr & 0x01) == 0:
            return sr
        if time.time() - start > timeout_s:
            raise TimeoutError(f'timeout waiting ready after {label}, sr=0x{sr:02X}')
        time.sleep(0.02)

def wren():
    cmd([0x06])
    time.sleep(0.005)
    sr = rdsr()
    if (sr & 0x02) == 0:
        raise RuntimeError(f'WREN failed, sr=0x{sr:02X}')
    return sr

def wrdi():
    cmd([0x04])
    time.sleep(0.005)

def read_flash(addr, n, chunk=252):
    data = bytearray()
    pos = 0
    while pos < n:
        ln = min(chunk, n-pos)
        a = addr + pos
        tx = [0x03, (a>>16)&255, (a>>8)&255, a&255] + [0]*ln
        b = cmd(tx)
        data.extend(b[4:4+ln])
        pos += ln
    return bytes(data)

def block_erase_64k(addr):
    if addr % 0x10000 != 0:
        raise ValueError('erase addr not 64k aligned')
    wren()
    cmd([0xD8, (addr>>16)&255, (addr>>8)&255, addr&255])
    sr = wait_ready(f'erase 0x{addr:06X}', timeout_s=120.0)
    return sr

def page_program(addr, data):
    if len(data) == 0 or len(data) > 256:
        raise ValueError('bad page len')
    if (addr & 0xFF) + len(data) > 256:
        raise ValueError('page crosses boundary')
    wren()
    tx = [0x02, (addr>>16)&255, (addr>>8)&255, addr&255] + list(data)
    cmd(tx)
    wait_ready(f'program 0x{addr:06X}', timeout_s=5.0)

h = dll.CH341OpenDevice(0)
ok = bool(h and h != wintypes.HANDLE(-1).value)
print('OPEN_HANDLE', h, 'OK', ok, flush=True)
if not ok:
    raise SystemExit(2)
try:
    if not dll.CH341SetStream(0, MODE):
        raise RuntimeError('CH341SetStream failed')
    print('SET_STREAM', hex(MODE), flush=True)

    # Verify stable JEDEC.
    for i in range(5):
        j = cmd([0x9F,0,0,0])
        print(f'JEDEC_{i}', j.hex(' '), flush=True)
        if bytes([0xEF,0x40,0x16]) not in j:
            raise SystemExit('NO_VALID_JEDEC_ABORT')
    print('JEDEC_STABLE_OK', flush=True)

    sr0 = rdsr()
    print('STATUS_INITIAL', f'0x{sr0:02X}', flush=True)
    # Test write-enable latch only, then disable it before destructive ops.
    sr_wel = wren()
    print('WREN_TEST_STATUS', f'0x{sr_wel:02X}', flush=True)
    wrdi()
    print('WRDI_STATUS', f'0x{rdsr():02X}', flush=True)

    # Address sanity read: first 256 of flash must match known original bootloader first bytes.
    first = read_flash(0, 256, chunk=64)
    first_sha = hashlib.sha256(first).hexdigest().upper()
    print('FLASH_FIRST256_SHA256', first_sha, flush=True)

    # Current mtd4 header before write.
    cur_hdr = read_flash(OFFSET, 64, chunk=64)
    print('CURRENT_MTD4_HEADER64', cur_hdr.hex(' '), flush=True)
    print('TARGET_MTD4_HEADER64', img[:64].hex(' '), flush=True)

    print('DESTRUCTIVE_WRITE_MTD4_START offset=0x%06X size=0x%06X end=0x%06X' % (OFFSET, SIZE, END), flush=True)

    # Erase 59 x 64 KiB blocks.
    blocks = SIZE // 0x10000
    if blocks * 0x10000 != SIZE:
        raise RuntimeError('mtd4 size not 64K multiple')
    for bi in range(blocks):
        a = OFFSET + bi*0x10000
        block_erase_64k(a)
        if bi % 4 == 0 or bi == blocks-1:
            print('ERASED_BLOCK %02d/%02d addr=0x%06X sr=0x%02X' % (bi+1, blocks, a, rdsr()), flush=True)

    # Verify erased sample: every 64K first 256 bytes, plus last 256 bytes.
    for bi in range(blocks):
        a = OFFSET + bi*0x10000
        sample = read_flash(a, 256, chunk=64)
        if sample != b'\xFF'*256:
            raise RuntimeError('erase verify failed at 0x%06X sha=%s first=%s' % (a, hashlib.sha256(sample).hexdigest().upper(), sample[:32].hex(' ')))
    tail = read_flash(END-256, 256, chunk=64)
    if tail != b'\xFF'*256:
        raise RuntimeError('erase verify failed at tail')
    print('ERASE_VERIFY_SAMPLES_OK', flush=True)

    # Program pages.
    total_pages = SIZE // 256
    for pi in range(total_pages):
        a = OFFSET + pi*256
        page = img[pi*256:(pi+1)*256]
        page_program(a, page)
        if pi % 1024 == 0 or pi == total_pages-1:
            print('PROGRAM_PAGE %05d/%05d addr=0x%06X' % (pi+1, total_pages, a), flush=True)

    print('PROGRAM_DONE_VERIFY_START', flush=True)
    # Verify by reading mtd4 back and hashing, also stop immediately on first mismatch.
    sha_v = hashlib.sha256()
    first_mismatch = None
    verified = 0
    for off in range(0, SIZE, 4096):
        rb = read_flash(OFFSET+off, 4096, chunk=252)
        tb = img[off:off+4096]
        sha_v.update(rb)
        if first_mismatch is None and rb != tb:
            for i, (a,b) in enumerate(zip(tb, rb)):
                if a != b:
                    first_mismatch = off+i, a, b
                    break
        verified += len(rb)
        if off % (512*1024) == 0:
            print('VERIFY_OFF 0x%06X' % off, flush=True)
    vsha = sha_v.hexdigest().upper()
    print('VERIFY_SIZE', verified, flush=True)
    print('VERIFY_SHA256', vsha, flush=True)
    print('VERIFY_MATCH_STOCK', vsha == expected_sha and first_mismatch is None, flush=True)
    if first_mismatch is not None:
        rel,a,b = first_mismatch
        raise RuntimeError('verify mismatch rel=0x%06X abs=0x%06X expected=%02X read=%02X' % (rel, OFFSET+rel, a, b))
    if vsha != expected_sha:
        raise RuntimeError('verify sha mismatch')
    print('RESTORE_MTD4_SUCCESS', flush=True)
finally:
    try:
        dll.CH341CloseDevice(0)
        print('CLOSED', flush=True)
    except Exception:
        pass
