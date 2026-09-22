from pathlib import Path
import re, sys, time, telnetlib, argparse
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
cmd = sys.argv[1] if len(sys.argv)>1 else 'echo READY'
wait = float(sys.argv[2]) if len(sys.argv)>2 else 5.0
print('TELNET_CONNECT', HOST, PORT, 'USER', USER, flush=True)
tn=telnetlib.Telnet(HOST, PORT, timeout=8)
def decode(d): return d.decode('utf-8', errors='backslashreplace').replace(PASS, '<password hidden>')
def drain(sec):
    end=time.time()+sec; out=b''
    while time.time()<end:
        try:
            d=tn.read_very_eager()
            if d:
                out += d; print(decode(d), end='', flush=True)
        except EOFError:
            break
        time.sleep(0.05)
    return out
def send(line, hidden=False):
    print('\n>>>', '<password hidden>' if hidden else line, flush=True)
    tn.write((line+'\r\n').encode('utf-8'))
    time.sleep(0.2)
drain(0.8); send(USER); drain(0.5); send(PASS, True); drain(0.8)
send(cmd); drain(wait)
send('exit'); drain(0.4)
try: tn.close()
except Exception: pass
print('\nTELNET_DONE', flush=True)
