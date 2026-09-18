from pathlib import Path
import socket, struct, time, hashlib, sys, threading
FILE = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\modified\mtd4_connectivity.bin')
DATA = FILE.read_bytes()
NAME = b'mtd4_connectivity.bin'
PORT = 69
HOST = '0.0.0.0'
print('TFTP_FILE', FILE, len(DATA), hashlib.sha256(DATA).hexdigest().upper(), flush=True)
print('TFTP_BIND', HOST, PORT, flush=True)

def serve_one(rrq, addr, sock):
    print('RRQ_FROM', addr, 'raw=', rrq[:120], flush=True)
    try:
        parts = rrq[2:].split(b'\0')
        filename = parts[0]
        mode = parts[1].lower() if len(parts)>1 else b'octet'
        print('RRQ_FILE', filename, 'MODE', mode, flush=True)
        if filename not in (NAME, b'/'+NAME):
            err = struct.pack('!HH', 5, 1) + b'File not found\0'
            sock.sendto(err, addr)
            return
        block = 1
        pos = 0
        client = addr
        while True:
            chunk = DATA[pos:pos+512]
            pkt = struct.pack('!HH', 3, block) + chunk
            # retransmit few times until ack
            for attempt in range(10):
                sock.sendto(pkt, client)
                sock.settimeout(3.0)
                try:
                    ack, a = sock.recvfrom(2048)
                except socket.timeout:
                    print('TIMEOUT block', block, 'attempt', attempt+1, flush=True)
                    continue
                if a != client:
                    continue
                if len(ack) >= 4:
                    op, bno = struct.unpack('!HH', ack[:4])
                    if op == 4 and bno == block:
                        break
                    elif op == 5:
                        print('ERROR_FROM_CLIENT', ack, flush=True)
                        return
            else:
                print('ABORT no ack block', block, flush=True)
                return
            if block % 512 == 0 or len(chunk) < 512:
                print('SENT_BLOCK', block, 'bytes', min(pos+len(chunk), len(DATA)), '/', len(DATA), flush=True)
            pos += len(chunk)
            if len(chunk) < 512:
                print('TFTP_DONE', flush=True)
                return
            block = (block + 1) & 0xffff
            if block == 0:
                block = 1
    finally:
        sock.settimeout(None)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST, PORT))
print('TFTP_READY', flush=True)
while True:
    data, addr = sock.recvfrom(2048)
    if len(data) >= 2:
        op = struct.unpack('!H', data[:2])[0]
        if op == 1:
            serve_one(data, addr, sock)
        else:
            print('UNEXPECTED_OP', op, 'from', addr, flush=True)
