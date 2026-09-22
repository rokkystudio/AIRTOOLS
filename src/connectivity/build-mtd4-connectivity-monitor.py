#!/usr/bin/env python3
"""
Builds a persistent ENDOSCOPE mtd4 image with connectivity plus a manual ra0 monitor experiment helper.

The Linux kernel byte layout stays unchanged. The rebuilt initramfs is smaller
than the original, and the unused remainder of the original embedded-initramfs
slot is filled with zero bytes. Linux initramfs unpacking accepts zero padding,
so the MIPS code following the slot remains at its original address.
"""

from __future__ import annotations

import hashlib
import lzma
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(r"D:\PROJECTS\ENDOSCOPE")
ORIGINAL_MTD4 = ROOT / "dumps" / "original" / "mtd4_kernel.bin"
SERVICE = ROOT / "artifacts" / "binaries" / "mipsel" / "endoscope-connectivity"
MONITOR_SCRIPT = ROOT / "src" / "monitor" / "ra0-monitor-experiment.sh"
MONITOR_README = ROOT / "src" / "monitor" / "README.ra0-monitor.txt"
MONITOR_PROBE_SOURCE = ROOT / "src" / "monitor" / "ra0_packet_probe.c"
LZMA_EXE = ROOT / "toolchain" / "lzma920" / "lzma.exe"
OUTPUT_DIR = ROOT / "dumps" / "modified"
OUTPUT_MTD4 = OUTPUT_DIR / "mtd4_connectivity_monitor.bin"

INNER_OFFSET = 0x43D000
INNER_SLOT_SIZE = 1_491_038

REMOVE_PATHS = {
    "bin/app_cam",
    "bin/app_detect",
    "sbin/video_ko.sh",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l2-int-device.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l1-compat.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/videodev.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l2-common.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/uvc/uvcvideo.ko",
}


@dataclass
class CpioEntry:
    """Represents one cpio newc entry and its metadata."""
    name: str
    ino: int
    mode: int
    uid: int
    gid: int
    nlink: int
    mtime: int
    data: bytes
    devmajor: int
    devminor: int
    rdevmajor: int
    rdevminor: int
    check: int


def unpack_uimage(image: bytes) -> tuple[bytearray, bytes]:
    """Returns the original uImage header and decompressed Linux kernel bytes."""
    if len(image) < 64 or image[:4] != b"\x27\x05\x19\x56":
        raise ValueError("mtd4 does not start with a U-Boot uImage header")

    header = bytearray(image[:64])
    payload_size = struct.unpack_from(">I", header, 12)[0]
    payload = image[64:64 + payload_size]
    kernel = lzma.decompress(payload, format=lzma.FORMAT_ALONE)
    return header, kernel


def extract_initramfs(kernel: bytes) -> tuple[bytes, bytes]:
    """Returns the decompressed built-in initramfs and the kernel bytes after its fixed slot."""
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    rootfs = decoder.decompress(kernel[INNER_OFFSET:])
    consumed = len(kernel[INNER_OFFSET:]) - len(decoder.unused_data)

    if consumed != INNER_SLOT_SIZE:
        raise ValueError(
            f"unexpected embedded initramfs stream size: {consumed}, "
            f"expected {INNER_SLOT_SIZE}"
        )

    if not rootfs.startswith(b"070701"):
        raise ValueError("embedded initramfs is not a cpio newc archive")

    tail = kernel[INNER_OFFSET + INNER_SLOT_SIZE:]
    return rootfs, tail


def parse_cpio(rootfs: bytes) -> list[CpioEntry]:
    """Parses a cpio newc archive and returns all entries except TRAILER!!!."""
    entries: list[CpioEntry] = []
    offset = 0

    while offset + 110 <= len(rootfs):
        if rootfs[offset:offset + 6] != b"070701":
            raise ValueError(f"invalid cpio magic at 0x{offset:X}")

        fields = [
            int(rootfs[offset + 6 + index * 8:offset + 14 + index * 8], 16)
            for index in range(13)
        ]
        (
            ino,
            mode,
            uid,
            gid,
            nlink,
            mtime,
            file_size,
            devmajor,
            devminor,
            rdevmajor,
            rdevminor,
            name_size,
            check,
        ) = fields

        name_start = offset + 110
        name = rootfs[name_start:name_start + name_size - 1].decode(
            "utf-8", "surrogateescape"
        )
        data_start = (name_start + name_size + 3) & ~3
        data = rootfs[data_start:data_start + file_size]
        offset = (data_start + file_size + 3) & ~3

        if name == "TRAILER!!!":
            break

        entries.append(
            CpioEntry(
                name=name.lstrip("./"),
                ino=ino,
                mode=mode,
                uid=uid,
                gid=gid,
                nlink=nlink,
                mtime=mtime,
                data=data,
                devmajor=devmajor,
                devminor=devminor,
                rdevmajor=rdevmajor,
                rdevminor=rdevminor,
                check=check,
            )
        )

    return entries


def patch_wifi_script(original: bytes) -> bytes:
    """Uses NVRAM network settings and starts the connectivity daemon before DHCP."""
    text = original.decode("utf-8")

    old_globals = '''#################################
ipaddr="192.168.10.123"
start="192.168.10.20"
end="192.168.10.100"
#################################
'''
    new_globals = '''#################################
ipaddr=§nvram_get 2860 lan_ipaddr§
start=§nvram_get 2860 dhcpStart§
end=§nvram_get 2860 dhcpEnd§
#################################
'''.replace("§", chr(96))

    if old_globals not in text:
        raise ValueError("wifi_ap.sh global DHCP block not found")
    text = text.replace(old_globals, new_globals, 1)

    marker = "\t# stop udhcpd\n"
    addition = '''\tnm=§nvram_get 2860 dhcpMask§
\tlease=§nvram_get 2860 dhcpLease§
\t[ -z "$ipaddr" ] && ipaddr="192.168.10.123"
\t[ -z "$start" ] && start="192.168.10.20"
\t[ -z "$end" ] && end="192.168.10.100"
\t[ -z "$nm" ] && nm="255.255.255.0"
\t[ -z "$lease" ] && lease="86400"

'''.replace("§", chr(96))

    if marker not in text:
        raise ValueError("wifi_ap.sh DHCP marker not found")
    text = text.replace(marker, addition + marker, 1)

    replacements = {
        '\techo "option subnet 255.255.255.0" >> /etc_ro/udhcpd.conf\n':
            '\techo "option subnet $nm" >> /etc_ro/udhcpd.conf\n',
        '\techo "option dns 168.95.1.1 8.8.8.8" >> /etc_ro/udhcpd.conf\n':
            '\techo "option dns $ipaddr" >> /etc_ro/udhcpd.conf\n',
        '\techo "option lease 86400" >> /etc_ro/udhcpd.conf\n':
            '\techo "option lease $lease" >> /etc_ro/udhcpd.conf\n',
    }

    for old, new in replacements.items():
        if old not in text:
            raise ValueError(f"wifi_ap.sh line not found: {old.strip()}")
        text = text.replace(old, new, 1)

    launch = '''\tkillall endoscope-connectivity 2>/dev/null
\t(trap "" HUP; /bin/endoscope-connectivity "$ipaddr" </dev/null >/dev/null 2>&1) &
'''
    daemon_marker = "\tudhcpd /etc_ro/udhcpd.conf\n"
    if daemon_marker not in text:
        raise ValueError("wifi_ap.sh udhcpd start not found")
    text = text.replace(daemon_marker, launch + daemon_marker, 1)

    return text.encode("utf-8")


def patch_rcs(original: bytes) -> bytes:
    """Removes camera/video startup commands while preserving the remaining boot sequence."""
    lines = original.decode("utf-8").splitlines()

    blocked = {
        "app_detect &",
        "/sbin/video_ko.sh install",
        "app_update &",
    }

    kept = [line for line in lines if line.strip() not in blocked]
    return ("\n".join(kept).rstrip() + "\n").encode("utf-8")


def transform_entries(entries: list[CpioEntry]) -> list[CpioEntry]:
    """Removes camera components, patches network scripts, and adds the connectivity daemon."""
    result: list[CpioEntry] = []
    service = SERVICE.read_bytes()
    app_detect_template = next(entry for entry in entries if entry.name == "bin/app_detect")
    inserted_service = False

    for entry in entries:
        if entry.name == "bin/app_detect":
            result.append(
                CpioEntry(
                    name="bin/endoscope-connectivity",
                    ino=entry.ino,
                    mode=entry.mode,
                    uid=entry.uid,
                    gid=entry.gid,
                    nlink=entry.nlink,
                    mtime=entry.mtime,
                    data=service,
                    devmajor=entry.devmajor,
                    devminor=entry.devminor,
                    rdevmajor=entry.rdevmajor,
                    rdevminor=entry.rdevminor,
                    check=entry.check,
                )
            )
            inserted_service = True
            continue

        if entry.name in REMOVE_PATHS:
            continue

        if entry.name == "sbin/wifi_ap.sh":
            entry = CpioEntry(**{**entry.__dict__, "data": patch_wifi_script(entry.data)})
        elif entry.name == "etc_ro/rcS":
            entry = CpioEntry(**{**entry.__dict__, "data": patch_rcs(entry.data)})

        result.append(entry)

    if not inserted_service:
        raise ValueError("app_detect slot not found for connectivity daemon")

    max_ino = max(entry.ino for entry in result)

    def add_monitor_file(name: str, data: bytes, mode: int) -> None:
        nonlocal max_ino
        max_ino += 1
        result.append(
            CpioEntry(
                name=name,
                ino=max_ino,
                mode=mode,
                uid=app_detect_template.uid,
                gid=app_detect_template.gid,
                nlink=1,
                mtime=app_detect_template.mtime,
                data=data,
                devmajor=app_detect_template.devmajor,
                devminor=app_detect_template.devminor,
                rdevmajor=0,
                rdevminor=0,
                check=0,
            )
        )

    add_monitor_file("bin/ra0-monitor-experiment", MONITOR_SCRIPT.read_bytes(), 0o100755)
    add_monitor_file("etc_ro/ra0-monitor-experiment.README", MONITOR_README.read_bytes(), 0o100644)
    add_monitor_file("etc_ro/ra0_packet_probe.c", MONITOR_PROBE_SOURCE.read_bytes(), 0o100644)

    return result


def newc_header(entry: CpioEntry) -> bytes:
    """Builds the 110-byte ASCII header for one cpio newc entry."""
    name_size = len(entry.name.encode("utf-8")) + 1
    fields = (
        entry.ino,
        entry.mode,
        entry.uid,
        entry.gid,
        entry.nlink,
        entry.mtime,
        len(entry.data),
        entry.devmajor,
        entry.devminor,
        entry.rdevmajor,
        entry.rdevminor,
        name_size,
        entry.check,
    )

    return b"070701" + b"".join(f"{value:08X}".encode("ascii") for value in fields)


def append_aligned(buffer: bytearray, data: bytes) -> None:
    """Appends bytes and pads the buffer to a four-byte cpio alignment boundary."""
    buffer.extend(data)
    while len(buffer) & 3:
        buffer.append(0)


def build_cpio(entries: list[CpioEntry]) -> bytes:
    """Builds a cpio newc archive and pads it to a 512-byte boundary."""
    archive = bytearray()
    max_ino = max(entry.ino for entry in entries)

    for entry in entries:
        append_aligned(archive, newc_header(entry) + entry.name.encode("utf-8") + b"\x00")
        append_aligned(archive, entry.data)

    trailer = CpioEntry(
        name="TRAILER!!!",
        ino=max_ino + 1,
        mode=0,
        uid=0,
        gid=0,
        nlink=1,
        mtime=0,
        data=b"",
        devmajor=0,
        devminor=0,
        rdevmajor=0,
        rdevminor=0,
        check=0,
    )
    append_aligned(archive, newc_header(trailer) + b"TRAILER!!!\x00")

    while len(archive) % 512:
        archive.append(0)

    return bytes(archive)


def compress_lzma_sdk(data: bytes, dictionary_bits: int) -> bytes:
    """Compresses bytes with LZMA SDK 9.20 using an explicit unpacked size and no EOS marker."""
    if not LZMA_EXE.is_file():
        raise FileNotFoundError(f"LZMA SDK encoder not found: {LZMA_EXE}")

    with tempfile.TemporaryDirectory(prefix="endoscope-lzma-") as temp_dir:
        temp = Path(temp_dir)
        input_path = temp / "input.bin"
        output_path = temp / "output.lzma"
        input_path.write_bytes(data)

        completed = subprocess.run(
            [
                str(LZMA_EXE),
                "e",
                str(input_path),
                str(output_path),
                f"-d{dictionary_bits}",
                "-lc3",
                "-lp0",
                "-pb2",
                "-mfbt4",
                "-fb64",
                "-a1",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                f"LZMA SDK encoder failed with code {completed.returncode}: "
                f"{completed.stderr.decode('ascii', 'replace')}"
            )

        compressed = output_path.read_bytes()

    if len(compressed) < 13:
        raise ValueError("LZMA SDK output is too short")

    unpacked_size = struct.unpack_from("<Q", compressed, 5)[0]
    if unpacked_size != len(data):
        raise ValueError(
            f"LZMA SDK wrote unpacked size {unpacked_size}, expected {len(data)}"
        )

    return compressed


def compress_inner(rootfs: bytes) -> bytes:
    """Compresses initramfs in the legacy .lzma form expected by the kernel."""
    return compress_lzma_sdk(rootfs, 20)


def compress_outer(kernel: bytes) -> bytes:
    """Compresses the kernel in the legacy .lzma form expected by U-Boot."""
    return compress_lzma_sdk(kernel, 25)


def build_uimage(original_header: bytearray, payload: bytes) -> bytes:
    """Updates uImage size and CRC fields while preserving load/entry/name metadata."""
    header = bytearray(original_header)

    struct.pack_into(">I", header, 4, 0)
    struct.pack_into(">I", header, 12, len(payload))
    struct.pack_into(">I", header, 24, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into(">I", header, 4, zlib.crc32(header) & 0xFFFFFFFF)

    return bytes(header) + payload


def main() -> None:
    """Builds and verifies a full replacement mtd4 partition image."""
    original = ORIGINAL_MTD4.read_bytes()
    header, kernel = unpack_uimage(original)
    old_rootfs, kernel_tail = extract_initramfs(kernel)

    old_entries = parse_cpio(old_rootfs)
    new_entries = transform_entries(old_entries)
    new_rootfs = build_cpio(new_entries)
    compressed_rootfs = compress_inner(new_rootfs)

    if len(compressed_rootfs) > INNER_SLOT_SIZE:
        raise ValueError(
            f"rebuilt initramfs is {len(compressed_rootfs)} bytes, "
            f"slot is only {INNER_SLOT_SIZE} bytes"
        )

    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    verified_rootfs = decoder.decompress(compressed_rootfs)
    if verified_rootfs != new_rootfs or not decoder.eof:
        raise AssertionError("rebuilt initramfs LZMA verification failed")

    inner_slot = compressed_rootfs + b"\x00" * (INNER_SLOT_SIZE - len(compressed_rootfs))
    patched_kernel = kernel[:INNER_OFFSET] + inner_slot + kernel_tail

    if len(patched_kernel) != len(kernel):
        raise AssertionError("kernel byte length changed")

    if patched_kernel[:INNER_OFFSET] != kernel[:INNER_OFFSET]:
        raise AssertionError("kernel bytes before initramfs changed")

    if patched_kernel[INNER_OFFSET + INNER_SLOT_SIZE:] != kernel[INNER_OFFSET + INNER_SLOT_SIZE:]:
        raise AssertionError("kernel bytes after initramfs changed")

    outer = compress_outer(patched_kernel)
    uimage = build_uimage(header, outer)

    old_payload_size = struct.unpack_from(">I", header, 12)[0]
    old_uimage_end = 64 + old_payload_size

    next_used = next(
        (
            index
            for index in range(old_uimage_end, len(original))
            if original[index] != 0xFF
        ),
        len(original),
    )

    if len(uimage) > next_used:
        raise ValueError(
            f"new uImage ends at 0x{len(uimage):X}, "
            f"next preserved data begins at 0x{next_used:X}"
        )

    output = bytearray(original)
    output[:next_used] = b"\xFF" * next_used
    output[:len(uimage)] = uimage

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MTD4.write_bytes(output)

    verify_header, verify_kernel = unpack_uimage(bytes(output))
    if verify_kernel != patched_kernel:
        raise AssertionError("outer uImage round-trip verification failed")

    data_size = struct.unpack_from(">I", verify_header, 12)[0]
    stored_data_crc = struct.unpack_from(">I", verify_header, 24)[0]
    actual_data_crc = zlib.crc32(output[64:64 + data_size]) & 0xFFFFFFFF
    if stored_data_crc != actual_data_crc:
        raise AssertionError("uImage data CRC mismatch")

    stored_header_crc = struct.unpack_from(">I", verify_header, 4)[0]
    header_for_crc = bytearray(verify_header)
    struct.pack_into(">I", header_for_crc, 4, 0)
    actual_header_crc = zlib.crc32(header_for_crc) & 0xFFFFFFFF
    if stored_header_crc != actual_header_crc:
        raise AssertionError("uImage header CRC mismatch")

    new_names = {entry.name for entry in new_entries}
    if "bin/endoscope-connectivity" not in new_names:
        raise AssertionError("connectivity daemon missing from rebuilt rootfs")
    if "bin/ra0-monitor-experiment" not in new_names:
        raise AssertionError("ra0 monitor experiment helper missing from rebuilt rootfs")
    if "etc_ro/ra0-monitor-experiment.README" not in new_names:
        raise AssertionError("ra0 monitor README missing from rebuilt rootfs")
    if any(path in new_names for path in REMOVE_PATHS):
        raise AssertionError("removed camera component still present")

    print(f"output={OUTPUT_MTD4}")
    print(f"bytes={len(output)}")
    print(f"sha256={hashlib.sha256(output).hexdigest().upper()}")
    print(f"new_rootfs_bytes={len(new_rootfs)}")
    print(f"old_rootfs_bytes={len(old_rootfs)}")
    print(f"inner_lzma_bytes={len(compressed_rootfs)}")
    print(f"inner_slot_bytes={INNER_SLOT_SIZE}")
    print(f"inner_zero_padding={INNER_SLOT_SIZE - len(compressed_rootfs)}")
    print(f"uimage_bytes={len(uimage)}")
    print(f"old_uimage_bytes={old_uimage_end}")
    print(f"next_preserved_data=0x{next_used:X}")
    print(f"service_bytes={SERVICE.stat().st_size}")


if __name__ == "__main__":
    main()
