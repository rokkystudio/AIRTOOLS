from pathlib import Path
import struct, sys
for dllpath in [r'C:\Users\rokky\Desktop\CH341\soft\Ch341A_Ver_134\CH341A.DLL', r'C:\Users\rokky\Desktop\CH341\soft\Ch341A_Ver_134\SPI.dll', r'C:\Windows\SysWOW64\CH341DLL.DLL']:
    p=Path(dllpath)
    print('FILE', p, 'exists', p.exists())
    if not p.exists(): continue
    b=p.read_bytes(); pe=struct.unpack_from('<I', b, 0x3c)[0]
    ns=struct.unpack_from('<H', b, pe+6)[0]; os=struct.unpack_from('<H', b, pe+20)[0]
    opt=pe+24; magic=struct.unpack_from('<H', b, opt)[0]
    export_rva, export_size = struct.unpack_from('<II', b, opt+(96 if magic==0x10b else 112))
    secs=[]; sb=opt+os
    for i in range(ns):
        off=sb+i*40; name=b[off:off+8].split(b'\0')[0].decode('ascii','ignore')
        vsize,va,rawsize,rawptr=struct.unpack_from('<IIII', b, off+8)
        secs.append((name,va,vsize,rawptr,rawsize))
    def rva2off(rva):
        for name,va,vsize,rawptr,rawsize in secs:
            if va <= rva < va+max(vsize,rawsize): return rawptr+(rva-va)
        raise ValueError(hex(rva))
    if not export_rva:
        print(' no exports'); continue
    exp=rva2off(export_rva)
    fields=struct.unpack_from('<IIHHIIIIIII', b, exp)
    num_names=fields[7]; addr_names=fields[9]
    names=[]
    for i in range(num_names):
        nrva=struct.unpack_from('<I', b, rva2off(addr_names)+i*4)[0]
        noff=rva2off(nrva)
        names.append(b[noff:b.index(b'\0',noff)].decode('ascii','ignore'))
    print(' exports', len(names))
    print('\n'.join(names[:120]))
