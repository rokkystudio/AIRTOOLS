from pathlib import Path
import struct
p = Path(r'C:\Windows\System32\CH341DLLA64.DLL')
b = p.read_bytes()
pe = struct.unpack_from('<I', b, 0x3c)[0]
num_sections = struct.unpack_from('<H', b, pe+6)[0]
opt_size = struct.unpack_from('<H', b, pe+20)[0]
opt = pe+24
magic = struct.unpack_from('<H', b, opt)[0]
if magic != 0x20b:
    raise SystemExit(f'not PE32+: {magic:x}')
export_rva, export_size = struct.unpack_from('<II', b, opt+112)
sections=[]
secbase=opt+opt_size
for i in range(num_sections):
    off=secbase+i*40
    name=b[off:off+8].split(b'\0')[0].decode('ascii','ignore')
    vsize, va, rawsize, rawptr = struct.unpack_from('<IIII', b, off+8)
    sections.append((name,va,vsize,rawptr,rawsize))
def rva2off(rva):
    for name,va,vsize,rawptr,rawsize in sections:
        if va <= rva < va + max(vsize, rawsize):
            return rawptr + (rva-va)
    raise ValueError(hex(rva))
exp = rva2off(export_rva)
(_,_,_,_,_,_,num_funcs,num_names,addr_funcs,addr_names,addr_ord) = struct.unpack_from('<IIHHIIIIIII', b, exp)
print('exports', num_names)
for i in range(num_names):
    nrva = struct.unpack_from('<I', b, rva2off(addr_names)+i*4)[0]
    noff = rva2off(nrva)
    s=b[noff:b.index(b'\0',noff)].decode('ascii','ignore')
    print(s)
