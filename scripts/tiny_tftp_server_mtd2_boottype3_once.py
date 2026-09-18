from pathlib import Path
import socket, struct, hashlib, sys, time
FILE = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\modified\mtd2_config_BootType3_full_preserve_config.bin')
DATA = FILE.read_bytes()
NAME = b'mtd2_config_BootType3.bin'
HOST = '0.0.0.0'
PORT = 69
print('TFTP_FILE', FILE, len(DATA), hashlib.sha256(DATA).hexdigest().upper(), flush=True)
print('TFTP_BIND', HOST, PORT, flush=True)

def serve_one(rrq, addr, sock):
    print('RRQ_FROM', addr, 'raw=', rrq[:120], flush=True)
    parts = rrq[2:].split(b'\0')
    filename = parts[0]
    mode = parts[1].lower() if len(parts)>1 else b'octet'
    print('RRQ_FILE', filename, 'MODE', mode, flush=True)
    if filename not in (NAME, b'/'+NAME):
        sock.sendto(struct.pack('!HH',5,1)+b'File not found\0', addr)
        return False
    block = 1
    pos = 0
    while True:
        chunk = DATA[pos:pos+512]
        pkt = struct.pack('!HH',3,block) + chunk
        ok = False
        for attempt in range(10):
            sock.sendto(pkt, addr)
            sock.settimeout(3.0)
            try:
                ack, a = sock.recvfrom(2048)
            except socket.timeout:
                print('TIMEOUT block', block, 'attempt', attempt+1, flush=True)
                continue
            if a != addr:
                continue
            if len(ack) >= 4:
                op, bno = struct.unpack('!HH', ack[:4])
                if op == 4 and bno == block:
                    ok = True
                    break
                if op == 5:
                    print('ERROR_FROM_CLIENT', ack, flush=True)
                    return False
        if not ok:
            print('ABORT no ack block', block, flush=True)
            return False
        if block % 64 == 0 or len(chunk) < 512:
            print('SENT_BLOCK', block, 'bytes', min(pos+len(chunk), len(DATA)), '/', len(DATA), flush=True)
        pos += len(chunk)
        if len(chunk) < 512:
            print('TFTP_DONE', flush=True)
            return True
        block = (block + 1) & 0xffff
        if block == 0: block = 1

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print('TFTP_READY', flush=True)
deadline = time.time() + 180
while time.time() < deadline:
    sock.settimeout(max(0.2, deadline-time.time()))
    try:
        data, addr = sock.recvfrom(2048)
    except socket.timeout:
        break
    if len(data) >= 2 and struct.unpack('!H', data[:2])[0] == 1:
        if serve_one(data, addr, sock):
            sys.exit(0)
print('TFTP_TIMEOUT_OR_FAIL', flush=True)
sys.exit(2)
