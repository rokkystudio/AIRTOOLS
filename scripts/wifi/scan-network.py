import socket, concurrent.futures, subprocess, ipaddress, time
hosts = ['192.168.3.1','192.168.10.123','192.168.10.1'] + [f'192.168.3.{i}' for i in range(1,255)] + [f'192.168.10.{i}' for i in range(1,255)]
ports = [23,80,21,69,8080]
seen=[]
def ping(ip):
    try:
        r=subprocess.run(['ping','-n','1','-w','250',ip],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=1)
        return r.returncode==0
    except Exception:
        return False
def tcp(ip,port):
    s=socket.socket(); s.settimeout(0.25)
    try:
        s.connect((ip,port)); s.close(); return True
    except Exception:
        try: s.close()
        except Exception: pass
        return False
live=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=80) as ex:
    futs={ex.submit(ping,ip):ip for ip in hosts}
    for fut in concurrent.futures.as_completed(futs):
        ip=futs[fut]
        if fut.result(): live.append(ip)
print('PING_LIVE', sorted(set(live), key=lambda x: tuple(map(int,x.split('.')))))
for ip in sorted(set(live + ['192.168.3.1','192.168.10.123']), key=lambda x: tuple(map(int,x.split('.')))):
    openp=[]
    for p in ports:
        if tcp(ip,p): openp.append(p)
    if openp:
        print('OPEN', ip, openp)
