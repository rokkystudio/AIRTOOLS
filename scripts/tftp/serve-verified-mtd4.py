from pathlib import Path
import socket
import struct
import hashlib

FILE = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\verified\mtd4_at_wpa2_airtools_wn723n_20260920.bin')
DATA = FILE.read_bytes()
NAMES = {b'mtd4_wn723n.bin', b'/mtd4_wn723n.bin', b'mtd4_connectivity.bin', b'/mtd4_connectivity.bin'}
print('TFTP_FILE', FILE, len(DATA), hashlib.sha256(DATA).hexdigest(), flush=True)
print('TFTP_NAMES', ','.join(name.decode('ascii', 'replace') for name in sorted(NAMES)), flush=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(('0.0.0.0', 69))
print('TFTP_READY', flush=True)

while True:
    req, addr = sock.recvfrom(2048)
    if len(req) < 2:
        continue
    op = struct.unpack('!H', req[:2])[0]
    if op != 1:
        print('UNEXPECTED_OP', op, addr, flush=True)
        continue
    name = req[2:].split(b'\0')[0]
    print('RRQ', addr, name, flush=True)
    if name not in NAMES:
        sock.sendto(struct.pack('!HH', 5, 1) + b'not found\0', addr)
        continue

    block = 1
    pos = 0
    sock.settimeout(3.0)
    while True:
        chunk = DATA[pos:pos + 512]
        packet = struct.pack('!HH', 3, block) + chunk
        ok = False
        for attempt in range(12):
            sock.sendto(packet, addr)
            try:
                ack, ack_addr = sock.recvfrom(2048)
            except socket.timeout:
                print('TIMEOUT', block, attempt + 1, flush=True)
                continue
            if ack_addr == addr and len(ack) >= 4:
                ack_op, ack_block = struct.unpack('!HH', ack[:4])
                if ack_op == 4 and ack_block == block:
                    ok = True
                    break
                if ack_op == 5:
                    print('CLIENT_ERROR', ack, flush=True)
                    break
        if not ok:
            print('ABORT', block, flush=True)
            break
        if block % 1024 == 0 or len(chunk) < 512:
            print('SENT_BLOCK', block, 'bytes', min(pos + len(chunk), len(DATA)), flush=True)
        pos += len(chunk)
        if len(chunk) < 512:
            print('TFTP_DONE', flush=True)
            break
        block = (block + 1) & 0xFFFF
        if block == 0:
            block = 1
    sock.settimeout(None)
