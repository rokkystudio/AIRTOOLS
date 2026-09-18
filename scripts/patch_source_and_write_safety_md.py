from pathlib import Path
import hashlib, time
ROOT=Path(r'D:\PROJECTS\ENDOSCOPE')
board=ROOT/r'toolchain\uboot-mt7628-src\src\lib_mips\board.c'
backup=board.with_suffix('.c.before-default-cli.patch')
text=board.read_text(encoding='utf-8', errors='replace')
if not backup.exists():
    backup.write_text(text, encoding='utf-8')
new=text
new=new.replace("unsigned char BootType='3', confirm=0;", "unsigned char BootType='4', confirm=0; /* patched: default to CLI, not flash boot */")
new=new.replace("\t\t\t\t\tBootType = '3';", "\t\t\t\t\tBootType = '4'; /* patched: invalid menu input falls back to CLI */")
if new==text:
    print('NO_SOURCE_CHANGE_MADE')
else:
    board.write_text(new, encoding='utf-8')
    print('SOURCE_PATCHED', board)
print('board_sha256', hashlib.sha256(board.read_bytes()).hexdigest().upper())
print('backup', backup, 'sha256', hashlib.sha256(backup.read_bytes()).hexdigest().upper())
# Create unified-ish small patch file
patch=ROOT/r'toolchain\uboot-mt7628-src\patches\default_cli_boottype4.patch'
patch.parent.mkdir(parents=True, exist_ok=True)
patch.write_text('''--- src/lib_mips/board.c\n+++ src/lib_mips/board.c\n@@\n-\tunsigned char BootType='3', confirm=0;\n+\tunsigned char BootType='4', confirm=0; /* patched: default to CLI, not flash boot */\n@@\n-\t\t\t\t\tBootType = '3';\n+\t\t\t\t\tBootType = '4'; /* patched: invalid menu input falls back to CLI */\n''', encoding='utf-8')
print('patch_file', patch)
# prevention markdown
md=ROOT/r'DO_NOT_BRICK_AGAIN.md'
md.write_text(f'''# Endoscope recovery safety rules\n\nLast updated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n## What happened\n\nThe device was bricked by flashing an mtd4 image whose U-Boot header checksum was OK but whose LZMA payload did not boot. The bootloader defaulted to option `3` (`System Boot system code via Flash`), so after the bad flash it looped into `LZMA ERROR 1` and UART recovery was unreliable.\n\nThe CH341A read confirmed that only mtd4 differed from the known-good dump:\n\n| Region | Offset | Size | Status |\n|---|---:|---:|---|\n| mtd1 bootloader | `0x000000` | `0x030000` | matched original |\n| mtd2 config | `0x030000` | `0x010000` | matched original |\n| mtd3 factory | `0x040000` | `0x010000` | matched original |\n| mtd4 kernel/rootfs | `0x050000` | `0x3B0000` | differed |\n\nCurrent CH341 dump comparison is saved here:\n\n`D:\\PROJECTS\\ENDOSCOPE\\dumps\\ch341\\flash_full_ch341_20260917-211155.compare.md`\n\n## Mandatory checks before any flash write\n\n1. Keep a full 4 MiB backup and per-partition backups. Do not proceed without SHA256 recorded.\n2. Never write bootloader (`0x000000..0x02FFFF`) unless there is a verified bootloader-specific reason and an external programmer backup.\n3. For normal firmware recovery write only mtd4: offset `0x50000`, length `0x3B0000`.\n4. Verify image size fits the partition exactly or is padded to the partition length.\n5. Verify uImage header: magic `0x27051956`, load `0x80000000`, entry `0x8000C150`, compression `3`/LZMA.\n6. Verify uImage header CRC and data CRC before flashing. Header checksum alone is not enough.\n7. Dry-run LZMA decompression of the payload before flashing. A valid uImage header can still contain an unbootable LZMA stream.\n8. Prefer RAM boot test via U-Boot `loadb`/`bootm` before writing to flash.\n9. If using CH341A, do at least two independent reads and compare SHA256 before any write.\n10. Do not trust a CH341A read unless JEDEC is stable (`EF 40 16`) and the first bytes match the known bootloader header.\n\n## CH341A hardware rules\n\nW25Q32BV / 25Q32 SOIC-8 pinout:\n\n```text\n          dot/key\n      1  CS#       VCC    8\n      2  DO/MISO   HOLD#  7\n      3  WP#       CLK    6\n      4  GND       DI/MOSI 5\n```\n\nRequired connections:\n\n```text\npin 1 CS#    -> CH341 CS\npin 2 DO     -> CH341 MISO\npin 3 WP#    -> 3.3V / high\npin 4 GND    -> CH341 GND\npin 5 DI     -> CH341 MOSI\npin 6 CLK    -> CH341 CLK\npin 7 HOLD#  -> 3.3V / high\npin 8 VCC    -> 3.3V\n```\n\nIf the board wakes up from the clip and the CH341A disconnects, stop. The programmer is powering the whole board or hitting a short/protection condition. Fix clip orientation/contact/power before continuing.\n\n## U-Boot safety patch\n\nSource file patched:\n\n`D:\\PROJECTS\\ENDOSCOPE\\toolchain\\uboot-mt7628-src\\src\\lib_mips\\board.c`\n\nPatch file:\n\n`D:\\PROJECTS\\ENDOSCOPE\\toolchain\\uboot-mt7628-src\\patches\\default_cli_boottype4.patch`\n\nBehavior change:\n\n```c\nBootType='3'  -> BootType='4'\ninvalid menu input fallback '3' -> '4'\n```\n\nExpected result after rebuilding and flashing a verified bootloader: cold boot defaults to U-Boot command line interface (`MT7628 #`) instead of automatically booting broken flash image option `3`.\n\nImportant: do not binary-patch or flash bootloader unless the patched binary is built/reviewed and the CH341A full backup is verified.\n\n## Current known-good recovery target\n\nKnown-good stock mtd4 file:\n\n`D:\\PROJECTS\\ENDOSCOPE\\dumps\\original\\mtd4_kernel.bin`\n\nWrite target, when ready:\n\n```text\nflash offset: 0x50000\nlength:       0x3B0000\n```\n\n''', encoding='utf-8')
print('safety_md', md)
print(md.read_text(encoding='utf-8')[:3000])
