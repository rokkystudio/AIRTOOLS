#!/usr/bin/env python3
"""
Preflight verification for AIRTOOLS mtd4 images.

The verifier validates boot-critical uImage properties, both LZMA layers, the
embedded initramfs, and the WN723N driver payload region used by the current
mtd4 image.
"""

from __future__ import annotations

import argparse
import hashlib
import lzma
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path


ROOT = Path(r"D:\PROJECTS\AIRTOOLS")
ORIGINAL = ROOT / "dumps" / "original" / "mtd4_kernel.bin"
DEFAULT_MODIFIED = ROOT / "dumps" / "modified" / "mtd4_base_connectivity_wn723n_autostart_airtools.bin"
DRIVER_LZMA = ROOT / "artifacts" / "drivers" / "rtl8188eus" / "8188eu_vendorabi_pm_skb_slim.ko.lzma"
LZMA_EXE = ROOT / "toolchain" / "lzma920" / "lzma.exe"

MTD4_SIZE = 0x3B0000
INNER_OFFSET = 0x43D000
INNER_SLOT_SIZE = 1_491_038
PAYLOAD_OFFSET = 0x340000

REMOVED_PATHS = {
    "bin/app_cam",
    "bin/app_detect",
    "sbin/video_ko.sh",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l2-int-device.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l1-compat.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/videodev.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/v4l2-common.ko",
    "lib/modules/2.6.36/kernel/drivers/media/video/uvc/uvcvideo.ko",
}


class VerificationError(RuntimeError):
    """Raised when a firmware image fails a boot-safety check."""


def check(condition: bool, message: str) -> None:
    """Raises VerificationError when a required condition is false."""
    if not condition:
        raise VerificationError(message)


def sha256(data: bytes) -> str:
    """Returns uppercase SHA-256 for display and comparison."""
    return hashlib.sha256(data).hexdigest().upper()


def parse_uimage(image: bytes, label: str) -> tuple[bytes, bytes, bytes]:
    """Validates a U-Boot uImage and returns header, compressed payload, kernel."""
    check(len(image) == MTD4_SIZE, f"{label}: partition size is {len(image)}, expected {MTD4_SIZE}")
    check(image[:4] == b"\x27\x05\x19\x56", f"{label}: invalid uImage magic")

    header = bytearray(image[:64])
    stored_header_crc = struct.unpack_from(">I", header, 4)[0]
    struct.pack_into(">I", header, 4, 0)
    actual_header_crc = zlib.crc32(header) & 0xFFFFFFFF
    check(stored_header_crc == actual_header_crc, f"{label}: uImage header CRC mismatch")

    header = image[:64]
    payload_size = struct.unpack_from(">I", header, 12)[0]
    check(0 < payload_size <= len(image) - 64, f"{label}: invalid uImage payload size {payload_size}")

    payload = image[64:64 + payload_size]
    stored_data_crc = struct.unpack_from(">I", header, 24)[0]
    actual_data_crc = zlib.crc32(payload) & 0xFFFFFFFF
    check(stored_data_crc == actual_data_crc, f"{label}: uImage data CRC mismatch")

    check(header[28] == 5, f"{label}: unexpected uImage OS {header[28]}")
    check(header[29] == 5, f"{label}: unexpected uImage architecture {header[29]}")
    check(header[30] == 2, f"{label}: unexpected uImage type {header[30]}")
    check(header[31] == 3, f"{label}: unexpected uImage compression {header[31]}")

    check(len(payload) >= 13, f"{label}: outer LZMA payload too short")
    unpacked_size = struct.unpack_from("<Q", payload, 5)[0]
    check(unpacked_size != 0xFFFFFFFFFFFFFFFF, f"{label}: outer LZMA has unknown unpacked size")

    try:
        kernel = lzma.decompress(payload, format=lzma.FORMAT_ALONE)
    except lzma.LZMAError as exc:
        raise VerificationError(f"{label}: Python cannot decode outer LZMA: {exc}") from exc

    check(len(kernel) == unpacked_size, f"{label}: outer LZMA size field does not match decoded kernel")
    return header, payload, kernel


def legacy_decode(stream: bytes, expected: bytes, label: str) -> None:
    """Decodes one .lzma stream with LZMA SDK 9.20 and compares exact output."""
    check(LZMA_EXE.is_file(), f"{label}: legacy LZMA decoder missing: {LZMA_EXE}")

    with tempfile.TemporaryDirectory(prefix="endoscope-preflight-") as temp_dir:
        temp = Path(temp_dir)
        source = temp / "source.lzma"
        decoded = temp / "decoded.bin"
        source.write_bytes(stream)

        completed = subprocess.run(
            [str(LZMA_EXE), "d", str(source), str(decoded)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        check(
            completed.returncode == 0,
            f"{label}: LZMA SDK 9.20 decoder failed with code {completed.returncode}",
        )
        actual = decoded.read_bytes()

    check(actual == expected, f"{label}: LZMA SDK decoded bytes differ from Python result")


def extract_inner(kernel: bytes, label: str) -> tuple[bytes, bytes, int]:
    """Decodes the embedded initramfs stream from its fixed kernel offset."""
    check(len(kernel) >= INNER_OFFSET + 13, f"{label}: kernel is too small for embedded initramfs")

    source = kernel[INNER_OFFSET:]
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)

    try:
        rootfs = decoder.decompress(source)
    except lzma.LZMAError as exc:
        raise VerificationError(f"{label}: embedded initramfs LZMA decode failed: {exc}") from exc

    check(decoder.eof, f"{label}: embedded initramfs LZMA stream has no end")
    consumed = len(source) - len(decoder.unused_data)
    stream = source[:consumed]

    check(consumed <= INNER_SLOT_SIZE, f"{label}: embedded initramfs exceeds reserved slot")
    check(len(stream) >= 13, f"{label}: embedded initramfs stream too short")
    unpacked_size = struct.unpack_from("<Q", stream, 5)[0]
    check(unpacked_size != 0xFFFFFFFFFFFFFFFF, f"{label}: inner LZMA has unknown unpacked size")
    check(unpacked_size == len(rootfs), f"{label}: inner LZMA size field mismatch")
    check(rootfs.startswith(b"070701"), f"{label}: decoded initramfs is not cpio newc")

    return rootfs, stream, consumed


def parse_cpio(rootfs: bytes) -> dict[str, bytes]:
    """Returns regular cpio entry payloads keyed by normalized path."""
    entries: dict[str, bytes] = {}
    offset = 0

    while offset + 110 <= len(rootfs):
        check(rootfs[offset:offset + 6] == b"070701", f"cpio: invalid magic at 0x{offset:X}")
        fields = [
            int(rootfs[offset + 6 + index * 8:offset + 14 + index * 8], 16)
            for index in range(13)
        ]
        file_size = fields[6]
        name_size = fields[11]
        name_start = offset + 110
        name_end = name_start + name_size
        check(name_end <= len(rootfs), "cpio: truncated name")
        name = rootfs[name_start:name_end - 1].decode("utf-8", "surrogateescape")
        data_start = (name_end + 3) & ~3
        data_end = data_start + file_size
        check(data_end <= len(rootfs), f"cpio: truncated data for {name}")
        data = rootfs[data_start:data_end]
        offset = (data_end + 3) & ~3

        if name == "TRAILER!!!":
            break

        entries[name.lstrip("./")] = data

    return entries


def verify_modified(modified_path: Path) -> None:
    """Runs all compatibility checks against the factory mtd4 image."""
    check(ORIGINAL.is_file(), f"factory mtd4 is missing: {ORIGINAL}")
    check(modified_path.is_file(), f"modified mtd4 is missing: {modified_path}")

    original_image = ORIGINAL.read_bytes()
    modified_image = modified_path.read_bytes()

    original_header, original_outer, original_kernel = parse_uimage(original_image, "original")
    modified_header, modified_outer, modified_kernel = parse_uimage(modified_image, "modified")

    check(modified_header[16:24] == original_header[16:24], "modified: load/entry addresses changed")
    check(modified_header[28:32] == original_header[28:32], "modified: uImage OS/arch/type/compression changed")
    check(modified_header[32:64] == original_header[32:64], "modified: uImage name changed")

    check(modified_outer[:5] == original_outer[:5], "modified: outer LZMA properties/dictionary differ from factory")
    check(
        struct.unpack_from("<Q", modified_outer, 5)[0] == len(original_kernel),
        "modified: outer LZMA unpacked size differs from factory kernel size",
    )
    check(len(modified_kernel) == len(original_kernel), "modified: decompressed kernel byte length changed")

    legacy_decode(modified_outer, modified_kernel, "modified outer LZMA")

    original_rootfs, original_inner, original_inner_size = extract_inner(original_kernel, "original")
    modified_rootfs, modified_inner, modified_inner_size = extract_inner(modified_kernel, "modified")

    check(original_inner_size == INNER_SLOT_SIZE, "original: unexpected embedded-initramfs slot size")
    check(modified_inner[:5] == original_inner[:5], "modified: inner LZMA properties/dictionary differ from factory")
    check(modified_inner_size <= INNER_SLOT_SIZE, "modified: inner LZMA exceeds factory slot")

    legacy_decode(modified_inner, modified_rootfs, "modified inner LZMA")

    check(
        modified_kernel[:INNER_OFFSET] == original_kernel[:INNER_OFFSET],
        "modified: kernel bytes before initramfs slot changed",
    )
    check(
        modified_kernel[INNER_OFFSET + INNER_SLOT_SIZE:] ==
        original_kernel[INNER_OFFSET + INNER_SLOT_SIZE:],
        "modified: kernel bytes after initramfs slot changed",
    )

    inner_padding = modified_kernel[
        INNER_OFFSET + modified_inner_size:
        INNER_OFFSET + INNER_SLOT_SIZE
    ]
    check(all(byte == 0 for byte in inner_padding), "modified: initramfs slot padding is not all zero")

    uimage_end = 64 + len(modified_outer)
    check(uimage_end <= PAYLOAD_OFFSET, f"modified: uImage ends at 0x{uimage_end:X}, payload starts at 0x{PAYLOAD_OFFSET:X}")
    check(
        all(byte == 0xFF for byte in modified_image[uimage_end:PAYLOAD_OFFSET]),
        "modified: padding between uImage and payload is not all 0xFF",
    )
    check(DRIVER_LZMA.is_file(), f"driver payload is missing: {DRIVER_LZMA}")
    driver_payload = DRIVER_LZMA.read_bytes()
    payload_end = PAYLOAD_OFFSET + len(driver_payload)
    check(payload_end <= MTD4_SIZE, "modified: driver payload exceeds mtd4 partition")
    check(
        modified_image[PAYLOAD_OFFSET:payload_end] == driver_payload,
        "modified: embedded driver payload differs from local release payload",
    )
    check(
        all(byte == 0xFF for byte in modified_image[payload_end:]),
        "modified: padding after driver payload is not all 0xFF",
    )

    entries = parse_cpio(modified_rootfs)
    check("bin/endoscope-connectivity" in entries, "modified: connectivity daemon missing")
    check(entries["bin/endoscope-connectivity"], "modified: connectivity daemon is empty")

    present_removed = sorted(path for path in REMOVED_PATHS if path in entries)
    check(not present_removed, f"modified: removed video components still present: {present_removed}")

    check("sbin/wifi_ap.sh" in entries, "modified: wifi_ap.sh missing")
    wifi = entries["sbin/wifi_ap.sh"].decode("utf-8", "replace")
    check("nvram_get 2860 lan_ipaddr" in wifi, "modified: wifi_ap.sh does not load LAN IP from NVRAM")
    check('option dns $ipaddr' in wifi, "modified: DHCP does not advertise the AP as DNS")
    check('/bin/endoscope-connectivity "$ipaddr"' in wifi, "modified: connectivity daemon is not auto-started")

    check("etc_ro/rcS" in entries, "modified: rcS missing")
    rcs = entries["etc_ro/rcS"].decode("utf-8", "replace")
    check("app_detect &" not in rcs, "modified: old app_detect startup remains")
    check("video_ko.sh install" not in rcs, "modified: video module startup remains")

    print("PREFLIGHT OK")
    print(f"original={ORIGINAL}")
    print(f"modified={modified_path}")
    print(f"modified_sha256={sha256(modified_image)}")
    print(f"partition_bytes={len(modified_image)}")
    print(f"outer_lzma_bytes={len(modified_outer)}")
    print(f"kernel_bytes={len(modified_kernel)}")
    print(f"inner_lzma_bytes={modified_inner_size}")
    print(f"inner_slot_bytes={INNER_SLOT_SIZE}")
    print(f"inner_zero_padding={len(inner_padding)}")
    print(f"rootfs_bytes={len(modified_rootfs)}")
    print(f"rootfs_entries={len(entries)}")
    print(f"service_bytes={len(entries['bin/endoscope-connectivity'])}")
    print("legacy_lzma_sdk_outer=OK")
    print("legacy_lzma_sdk_inner=OK")
    print(f"payload_offset=0x{PAYLOAD_OFFSET:X}")
    print(f"payload_bytes={len(driver_payload)}")
    print(f"payload_sha256={sha256(driver_payload)}")
    print("payload_region=OK")


def main() -> None:
    """Parses command-line arguments and verifies the selected image."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "image",
        nargs="?",
        type=Path,
        default=DEFAULT_MODIFIED,
        help="modified mtd4 image to verify",
    )
    args = parser.parse_args()

    try:
        verify_modified(args.image.resolve())
    except VerificationError as exc:
        print(f"PREFLIGHT FAILED: {exc}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
