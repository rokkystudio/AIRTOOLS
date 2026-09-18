from pathlib import Path
import socket, struct, hashlib, time
OUTDIR = Path(r'D:\PROJECTS\ENDOSCOPE\dumps\modified')
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT = OUTDIR / 'mtd4_connectivity.roundtrip.bin'
HOST='0.0.0.0'; PORT=69
print('TFTP_WRQ_BIND', HOST, PORT, flush=True)
print('TFTP_WRQ_OUT', OUT, flush=True)
sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((HOST,PORT))
print('TFTP_WRQ_READY', flush=True)
while True:
    data, addr = sock.recvfrom(2048)
    if len(data)<2: continue
    op=struct.unpack('!H', data[:2])[0]
    if op != 2:
        print('UNEXPECTED_OP', op, 'from', addr, flush=True)
        continue
    parts=data[2:].split(b'\0')
    name=parts[0]
    mode=parts[1].lower() if len(parts)>1 else b'octet'
    print('WRQ_FROM', addr, 'FILE', name, 'MODE', mode, flush=True)
    f=open(OUT,'wb')
    client=addr
    expected=1
    # ACK block 0
    sock.sendto(struct.pack('!HH',4,0), client)
    total=0
    sock.settimeout(10.0)
    while True:
        try:
            pkt,a=sock.recvfrom(4096)
        except socket.timeout:
            print('TIMEOUT waiting block', expected, flush=True)
            break
        if a != client:
            continue
        if len(pkt)<4:
            continue
        op2,bno=struct.unpack('!HH', pkt[:4])
        if op2 == 5:
            print('ERROR_FROM_CLIENT', pkt, flush=True)
            break
        if op2 != 3:
            print('UNEXPECTED_OP2', op2, 'block', bno, flush=True)
            continue
        chunk=pkt[4:]
        if bno == expected:
            f.write(chunk)
            total += len(chunk)
            sock.sendto(struct.pack('!HH',4,bno), client)
            if bno % 512 == 0 or len(chunk)<512:
                print('RECV_BLOCK', bno, 'bytes', total, flush=True)
            expected = (expected + 1) & 0xffff
            if expected == 0: expected=1
            if len(chunk) < 512:
                break
        else:
            # ACK duplicate/out of order last block number seen
            sock.sendto(struct.pack('!HH',4,bno), client)
    f.close()
    data=OUT.read_bytes() if OUT.exists() else b''
    print('WRQ_DONE size', len(data), 'sha256', hashlib.sha256(data).hexdigest().upper(), flush=True)
    break
