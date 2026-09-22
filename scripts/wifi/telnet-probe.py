from pathlib import Path
import re, sys, time, telnetlib
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='backslashreplace')
    sys.stderr.reconfigure(encoding='utf-8', errors='backslashreplace')
except Exception:
    pass
cfg = Path('scripts/telnet/endoscope-telnet.local.ps1').read_text(encoding='utf-8', errors='replace')
def get(name):
    m=re.search(r"\$"+re.escape(name)+r"\s*=\s*'([^']*)'", cfg)
    return m.group(1) if m else None
HOST=get('EndoscopeTelnetHost') or '192.168.10.123'
PORT=int(get('EndoscopeTelnetPort') or 23)
USER=get('EndoscopeTelnetUser') or 'molink'
PASS=get('EndoscopeTelnetPassword') or ''
cmd = "echo READY; uname -a; cat /proc/mtd; ls -l /dev/mtd* 2>/dev/null; df -h /tmp; for x in mtd_write mtd write flashcp flash dd cat tftp wget nc md5sum sha256sum busybox; do echo -n $x=; which $x 2>/dev/null || echo no; done; ps | head -n 20"
print('TELNET_CONNECT', HOST, PORT, 'USER', USER, flush=True)
tn = telnetlib.Telnet(HOST, PORT, timeout=8)
def show(data):
    if not data: return
    text = data.decode('utf-8', errors='backslashreplace').replace(PASS, '<password hidden>')
    print(text, end='', flush=True)
def read_some(sec=1.0):
    end=time.time()+sec
    out=b''
    while time.time()<end:
        try:
            d=tn.read_very_eager()
            if d:
                out += d; show(d)
        except EOFError:
            break
        time.sleep(0.05)
    return out
def send(line, hidden=False):
    print('\n>>>', '<password hidden>' if hidden else line, flush=True)
    tn.write((line+'\r\n').encode('utf-8'))
    time.sleep(0.2)
read_some(1.0)
send(USER); read_some(0.8)
send(PASS, hidden=True); read_some(1.2)
send(cmd); read_some(8.0)
send('exit'); read_some(1.0)
tn.close()
print('\nTELNET_DONE', flush=True)
