# mtd4 connectivity patch preflight

- generated: 2026-09-17 23:25:44
- stock: `D:\PROJECTS\ENDOSCOPE\dumps\original\mtd4_kernel.bin`
- stock size/SHA256: `3866624` / `72904FD990D724D81CF2EBD3C1E812954C55422442D16CAB7C0E152FF3610C2D`
- patch: `D:\PROJECTS\ENDOSCOPE\dumps\modified\mtd4_connectivity.bin`
- patch size/SHA256: `3866624` / `7318F8085362E294C9DDA624CE6FF1E7C137930CF30760A2D2341B53F0E803F7`
- size ok 0x3B0000: `True`
- patch equals stock: `False`

## uImage stock
- magic: `0x27051956`
- hcrc: `0x42587649`
- hcrc_calc: `0x42587649`
- hcrc_ok: `True`
- size: `3018696`
- load: `0x80000000`
- entry: `0x8000C150`
- dcrc: `0x2668279F`
- dcrc_calc: `0x2668279F`
- dcrc_ok: `True`
- os: `5`
- arch: `5`
- type: `2`
- comp: `3`
- name: `Linux Kernel Image`
- known_ok: `True`

## uImage patch
- magic: `0x27051956`
- hcrc: `0x135D80FE`
- hcrc_calc: `0x135D80FE`
- hcrc_ok: `True`
- size: `2927713`
- load: `0x80000000`
- entry: `0x8000C150`
- dcrc: `0x6E2780A2`
- dcrc_calc: `0x6E2780A2`
- dcrc_ok: `True`
- os: `5`
- arch: `5`
- type: `2`
- comp: `3`
- name: `Linux Kernel Image`
- known_ok: `True`
