import socket, sys, pathlib, hashlib, time
out=pathlib.Path(sys.argv[1])
s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
s.bind(('0.0.0.0',69))
s.settimeout(20)
print('TFTP_WRQ_READY', out, flush=True)
data,addr=s.recvfrom(2048)
op=int.from_bytes(data[:2],'big')
print('FIRST',op,addr,data[:80],flush=True)
if op!=2: raise SystemExit('expected WRQ')
# ack block 0
s.sendto(b'\x00\x04\x00\x00', addr)
received=bytearray(); expected=1
while True:
    pkt,addr2=s.recvfrom(2048)
    op=int.from_bytes(pkt[:2],'big')
    blk=int.from_bytes(pkt[2:4],'big')
    if op!=3:
        print('OP',op,'BLK',blk,flush=True); break
    if blk==expected:
        received += pkt[4:]
        if len(received) % 16384 == 0 or len(pkt[4:]) < 512:
            print('RECV',blk,len(received),flush=True)
        expected=(expected+1)&0xffff
    s.sendto(b'\x00\x04'+pkt[2:4], addr)
    if len(pkt[4:]) < 512:
        break
out.write_bytes(received)
print('DONE size', len(received), 'sha256', hashlib.sha256(received).hexdigest().upper(), flush=True)
