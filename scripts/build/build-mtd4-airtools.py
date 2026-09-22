#!/usr/bin/env python3
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
BASE_MTD4 = ROOT / "dumps" / "bases" / "mtd4_connectivity_base_20260916.bin"
BIN_DIR = ROOT / "artifacts" / "binaries" / "mipsel"
EXTRACTOR = BIN_DIR / "mtd4_lzma_extract_8188eu_mipsel"
RTAPCAP = BIN_DIR / "rtap_capture_mipsel"
AIRODUMP = BIN_DIR / "airodump_mipsel"
AIREPLAY = BIN_DIR / "aireplay_mipsel"
AIRTOOLS = BIN_DIR / "airtools_mipsel"
DRIVER_LZMA = ROOT / "artifacts" / "drivers" / "rtl8188eus" / "8188eu_vendorabi_pm_skb_slim.ko.lzma"
DRIVER_KO = ROOT / "artifacts" / "drivers" / "rtl8188eus" / "8188eu_vendorabi_pm_skb_slim.ko"
LZMA_EXE = ROOT / "toolchain" / "lzma920" / "lzma.exe"
OUTPUT_DIR = ROOT / "dumps" / "modified"
OUTPUT_MTD4 = OUTPUT_DIR / "mtd4_base_connectivity_wn723n_autostart_airtools.bin"

INNER_OFFSET = 0x43D000
INNER_SLOT_SIZE = 1_491_038
MTD4_SIZE = 0x3B0000
PAYLOAD_OFFSET = 0x340000

EXTRACTOR_PATH = "bin/wn723n-extract"
MONITOR_HELPER_PATH = "bin/wn723n-monitor"
RTAPCAP_PATH = "bin/rtapcap"
AIRODUMP_PATH = "bin/airodump"
AIREPLAY_PATH = "bin/aireplay"
AIRTOOLS_PATH = "bin/airtools"
AIRWIFI_PATH = "bin/airwifi"
README_PATH = "etc_ro/wn723n-monitor.README"

REPLACE_PATHS = {EXTRACTOR_PATH, MONITOR_HELPER_PATH, RTAPCAP_PATH, AIRODUMP_PATH, AIREPLAY_PATH, AIRTOOLS_PATH, AIRWIFI_PATH, README_PATH}

HELPER = r'''#!/bin/sh
IF=wlan0
CHANNEL=${2:-11}
KO=/tmp/8188eu.ko

usage() {
    echo "Usage: /bin/wn723n-monitor {status|extract|load|monitor [channel]|capture|usb|reboot-clean}"
    echo "Default monitor channel: 11"
    echo "The 8188eu driver is stored compressed in mtd4 and is started automatically at boot."
}

loaded() {
    grep '^8188eu ' /proc/modules >/dev/null 2>&1
}

status() {
    echo "__MODULES__"
    cat /proc/modules
    echo "__USB__"
    cat /proc/bus/usb/devices 2>/dev/null
    echo "__RA1__"
    ifconfig ra1 2>/dev/null
    echo "__WLAN0__"
    ifconfig wlan0 2>/dev/null
    iwconfig wlan0 2>/dev/null
    echo "__WLAN0_TYPE__"
    cat /sys/class/net/wlan0/type 2>/dev/null
}

extract_driver() {
    mkdir -p /tmp 2>/dev/null
    if [ ! -x /bin/wn723n-extract ]; then
        echo "MISSING_EXTRACTOR:/bin/wn723n-extract"
        return 2
    fi
    /bin/wn723n-extract
    ret=$?
    echo "EXTRACT_RET:$ret"
    return $ret
}

load_driver() {
    if loaded; then
        echo "INSMOD_RET:already-loaded"
        return 0
    fi

    if [ ! -f "$KO" ]; then
        extract_driver || return $?
    fi

    insmod "$KO"
    ret=$?
    echo "INSMOD_RET:$ret"
    return $ret
}

start_monitor() {
    load_driver || return $?

    ifconfig "$IF" up
    echo "WLAN0_UP_RET:$?"

    iwconfig "$IF" mode monitor
    echo "MODE_RET:$?"

    iwconfig "$IF" channel "$CHANNEL"
    echo "CHANNEL_RET:$?"

    echo "__MONITOR_STATE__"
    iwconfig "$IF" 2>/dev/null
    echo "__WLAN0_TYPE__"
    cat /sys/class/net/$IF/type 2>/dev/null
    echo "__WLAN0_COUNTERS__"
    cat /proc/net/dev | grep "$IF"
}

case "$1" in
    status)
        status
        ;;
    usb)
        cat /proc/bus/usb/devices 2>/dev/null
        ;;
    extract)
        extract_driver
        ;;
    load)
        load_driver
        ;;
    monitor)
        start_monitor
        ;;
    capture)
        if [ ! -x /bin/rtapcap ]; then
            echo "MISSING_CAPTURE_HELPER:/bin/rtapcap"
            exit 2
        fi
        /bin/rtapcap
        echo "RTAPCAP_RET:$?"
        ;;
    reboot-clean)
        reboot -f
        ;;
    *)
        usage
        exit 1
        ;;
esac
'''

AIRWIFI = r'''#!/bin/sh
CMD="$1"
SSID="$2"
PASS="$3"

valid_alnum() {
    case "$1" in
        "") return 1 ;;
        *[!A-Za-z0-9]*) return 1 ;;
        *) return 0 ;;
    esac
}

apply_wifi() {
    ssid_len=`expr length "$SSID"`
    pass_len=`expr length "$PASS"`

    valid_alnum "$SSID" || exit 11
    valid_alnum "$PASS" || exit 12
    [ "$ssid_len" -ge 1 ] || exit 13
    [ "$ssid_len" -le 32 ] || exit 14
    [ "$pass_len" -ge 8 ] || exit 15
    [ "$pass_len" -le 63 ] || exit 16

    echo "ssid=$SSID" > /tmp/airwifi.state
    echo "pass_len=$pass_len" >> /tmp/airwifi.state
    echo "auth=WPA2PSK" >> /tmp/airwifi.state

    config_save.sh ssid "$SSID" >/dev/null 2>&1
    config_save.sh passwd "$PASS" >/dev/null 2>&1

    iwpriv ra1 set SSID="$SSID" >/dev/null 2>&1
    iwpriv ra1 set AuthMode=WPA2PSK >/dev/null 2>&1
    iwpriv ra1 set EncrypType=AES >/dev/null 2>&1
    iwpriv ra1 set WPAPSK="$PASS" >/dev/null 2>&1

    echo "OK ssid=$SSID pass_len=$pass_len" >> /tmp/airwifi.state
    exit 0
}

case "$CMD" in
    apply-delayed)
        sleep 1
        apply_wifi
        ;;
    apply)
        apply_wifi
        ;;
    *)
        echo "Usage: /bin/airwifi {apply|apply-delayed} <ssid> <password>"
        exit 1
        ;;
esac
'''

README = f"""WN723N RTL8188EUS monitor support for ENDOSCOPE\n\nBase image: dumps\\bases\\mtd4_connectivity_base_20260916.bin\n\nThe built-in MT7628 ra1 interface remains the normal ENDOSCOPE AP.\nThe external TP-LINK WN723N / RTL8188EUS driver is stored compressed in mtd4\nat offset 0x{PAYLOAD_OFFSET:06X}. It is started automatically from wifi_ap.sh dhcp_init after the normal ra1 AP and connectivity-check service startup.\n\nManual sequence:\n\n    /bin/wn723n-monitor status\n    /bin/wn723n-monitor monitor 11\n    /bin/wn723n-monitor capture\n    /bin/wn723n-monitor reboot-clean\n\nExpected monitor state:\n\n    wlan0 Mode:Monitor\n    /sys/class/net/wlan0/type = 803\n\nRuntime extraction writes /tmp/8188eu.ko. Returning to the ordinary clean state\nis done by rebooting. Boot autoload is configured: /bin/airtools runs from wifi_ap.sh dhcp_init, next to endoscope-connectivity and udhcpd, and starts wn723n-monitor plus airodump collector.\n"""


@dataclass
class CpioEntry:
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
    if len(image) < 64 or image[:4] != b"\x27\x05\x19\x56":
        raise ValueError("mtd4 does not start with a U-Boot uImage header")
    header = bytearray(image[:64])
    payload_size = struct.unpack_from(">I", header, 12)[0]
    payload = image[64:64 + payload_size]
    kernel = lzma.decompress(payload, format=lzma.FORMAT_ALONE)
    return header, kernel


def extract_initramfs(kernel: bytes) -> tuple[bytes, bytes]:
    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    rootfs = decoder.decompress(kernel[INNER_OFFSET:])
    consumed = len(kernel[INNER_OFFSET:]) - len(decoder.unused_data)
    if consumed > INNER_SLOT_SIZE:
        raise ValueError(f"embedded initramfs stream size {consumed} exceeds slot {INNER_SLOT_SIZE}")
    if not rootfs.startswith(b"070701"):
        raise ValueError("embedded initramfs is not a cpio newc archive")
    return rootfs, kernel[INNER_OFFSET + INNER_SLOT_SIZE:]


def parse_cpio(rootfs: bytes) -> list[CpioEntry]:
    entries: list[CpioEntry] = []
    offset = 0
    while offset + 110 <= len(rootfs):
        if rootfs[offset:offset + 6] != b"070701":
            raise ValueError(f"invalid cpio magic at 0x{offset:X}")
        fields = [int(rootfs[offset + 6 + index * 8:offset + 14 + index * 8], 16) for index in range(13)]
        ino, mode, uid, gid, nlink, mtime, file_size, devmajor, devminor, rdevmajor, rdevminor, name_size, check = fields
        name_start = offset + 110
        name = rootfs[name_start:name_start + name_size - 1].decode("utf-8", "surrogateescape")
        data_start = (name_start + name_size + 3) & ~3
        data = rootfs[data_start:data_start + file_size]
        offset = (data_start + file_size + 3) & ~3
        if name == "TRAILER!!!":
            break
        entries.append(CpioEntry(name=name.lstrip("./"), ino=ino, mode=mode, uid=uid, gid=gid, nlink=nlink, mtime=mtime, data=data, devmajor=devmajor, devminor=devminor, rdevmajor=rdevmajor, rdevminor=rdevminor, check=check))
    return entries


def add_file(entries: list[CpioEntry], template: CpioEntry, name: str, data: bytes, mode: int) -> None:
    max_ino = max(entry.ino for entry in entries)
    entries.append(CpioEntry(name=name, ino=max_ino + 1, mode=mode, uid=template.uid, gid=template.gid, nlink=1, mtime=template.mtime, data=data, devmajor=template.devmajor, devminor=template.devminor, rdevmajor=0, rdevminor=0, check=0))


def transform_entries(entries: list[CpioEntry]) -> list[CpioEntry]:
    for path in (EXTRACTOR, RTAPCAP, AIRODUMP, AIREPLAY, AIRTOOLS, DRIVER_LZMA, DRIVER_KO):
        if not path.is_file():
            raise FileNotFoundError(path)
    result = [entry for entry in entries if entry.name not in REPLACE_PATHS]
    template = next((entry for entry in result if entry.name == "bin/endoscope-connectivity"), None)
    if template is None:
        template = next((entry for entry in result if entry.name.startswith("bin/")), None)
    if template is None:
        raise ValueError("no template entry found for new rootfs files")
    add_file(result, template, EXTRACTOR_PATH, EXTRACTOR.read_bytes(), 0o100755)
    add_file(result, template, MONITOR_HELPER_PATH, HELPER.encode("utf-8"), 0o100755)
    add_file(result, template, RTAPCAP_PATH, RTAPCAP.read_bytes(), 0o100755)
    add_file(result, template, AIRODUMP_PATH, AIRODUMP.read_bytes(), 0o100755)
    add_file(result, template, AIREPLAY_PATH, AIREPLAY.read_bytes(), 0o100755)
    add_file(result, template, AIRTOOLS_PATH, AIRTOOLS.read_bytes(), 0o100755)
    add_file(result, template, AIRWIFI_PATH, AIRWIFI.encode("utf-8"), 0o100755)
    add_file(result, template, README_PATH, README.encode("utf-8"), 0o100644)

    for entry in result:
        if entry.name == "sbin/wifi_ap.sh":
            old = b"ap_name=`flash -n`"
            new = b'ap_name="AT"'
            if old not in entry.data:
                raise ValueError("wifi_ap.sh ap_name flash read pattern not found")
            entry.data = entry.data.replace(old, new, 1)

            old_pass = b"ap_password=`flash -p`"
            new_pass = b'ap_password="12345678"'
            if old_pass not in entry.data:
                raise ValueError("wifi_ap.sh ap_password flash read pattern not found")
            entry.data = entry.data.replace(old_pass, new_pass, 1)

            marker = (
                b'\tkillall endoscope-connectivity 2>/dev/null\n'
                b'\t(trap "" HUP; /bin/endoscope-connectivity "$ipaddr" </dev/null >/dev/null 2>&1) &\n'
                b'\tudhcpd /etc_ro/udhcpd.conf'
            )
            replacement = (
                b'\tkillall endoscope-connectivity 2>/dev/null\n'
                b'\t(trap "" HUP; /bin/endoscope-connectivity "$ipaddr" </dev/null >/dev/null 2>&1) &\n'
                b'\tkillall airtools 2>/dev/null\n'
                b'\tkillall airodump 2>/dev/null\n'
                b'\t(trap "" HUP; /bin/airtools </dev/null >/dev/null 2>&1) &\n'
                b'\tudhcpd /etc_ro/udhcpd.conf'
            )
            if marker not in entry.data:
                raise ValueError("wifi_ap.sh connectivity startup marker not found")
            entry.data = entry.data.replace(marker, replacement, 1)
            break
    else:
        raise ValueError("sbin/wifi_ap.sh not found for SSID and airtools patch")

    for entry in result:
        if entry.name == "bin/endoscope-connectivity":
            old = b"ENDOSCOPE local network\n"
            if old in entry.data:
                entry.data = entry.data.replace(old, b"AT local network\n" + b" " * (len(old) - len(b"AT local network\n")), 1)
            break

    return result


def newc_header(entry: CpioEntry) -> bytes:
    name_size = len(entry.name.encode("utf-8")) + 1
    fields = (entry.ino, entry.mode, entry.uid, entry.gid, entry.nlink, entry.mtime, len(entry.data), entry.devmajor, entry.devminor, entry.rdevmajor, entry.rdevminor, name_size, entry.check)
    return b"070701" + b"".join(f"{value:08X}".encode("ascii") for value in fields)


def append_aligned(buffer: bytearray, data: bytes) -> None:
    buffer.extend(data)
    while len(buffer) & 3:
        buffer.append(0)


def build_cpio(entries: list[CpioEntry]) -> bytes:
    archive = bytearray()
    max_ino = max(entry.ino for entry in entries)
    for entry in entries:
        append_aligned(archive, newc_header(entry) + entry.name.encode("utf-8") + b"\x00")
        append_aligned(archive, entry.data)
    trailer = CpioEntry(name="TRAILER!!!", ino=max_ino + 1, mode=0, uid=0, gid=0, nlink=1, mtime=0, data=b"", devmajor=0, devminor=0, rdevmajor=0, rdevminor=0, check=0)
    append_aligned(archive, newc_header(trailer) + b"TRAILER!!!\x00")
    while len(archive) % 512:
        archive.append(0)
    return bytes(archive)


def compress_lzma_sdk(data: bytes, dictionary_bits: int) -> bytes:
    if not LZMA_EXE.is_file():
        raise FileNotFoundError(LZMA_EXE)
    with tempfile.TemporaryDirectory(prefix="endoscope-lzma-") as temp_dir:
        temp = Path(temp_dir)
        input_path = temp / "input.bin"
        output_path = temp / "output.lzma"
        input_path.write_bytes(data)
        completed = subprocess.run([str(LZMA_EXE), "e", str(input_path), str(output_path), f"-d{dictionary_bits}", "-lc3", "-lp0", "-pb2", "-mfbt4", "-fb64", "-a1"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.decode("ascii", "replace"))
        compressed = output_path.read_bytes()
    if len(compressed) < 13:
        raise ValueError("LZMA SDK output is too short")
    unpacked_size = struct.unpack_from("<Q", compressed, 5)[0]
    if unpacked_size != len(data):
        raise ValueError(f"LZMA unpacked size {unpacked_size}, expected {len(data)}")
    return compressed


def build_uimage(original_header: bytearray, payload: bytes) -> bytes:
    header = bytearray(original_header)
    struct.pack_into(">I", header, 4, 0)
    struct.pack_into(">I", header, 12, len(payload))
    struct.pack_into(">I", header, 24, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into(">I", header, 4, zlib.crc32(header) & 0xFFFFFFFF)
    return bytes(header) + payload


def main() -> None:
    base = BASE_MTD4.read_bytes()
    if len(base) != MTD4_SIZE:
        raise ValueError(f"unexpected mtd4 size: {len(base)}")
    driver_payload = DRIVER_LZMA.read_bytes()
    if PAYLOAD_OFFSET + len(driver_payload) > len(base):
        raise ValueError("driver payload exceeds mtd4")

    header, kernel = unpack_uimage(base)
    old_rootfs, kernel_tail = extract_initramfs(kernel)
    old_entries = parse_cpio(old_rootfs)
    new_entries = transform_entries(old_entries)
    new_rootfs = build_cpio(new_entries)
    compressed_rootfs = compress_lzma_sdk(new_rootfs, 20)
    if len(compressed_rootfs) > INNER_SLOT_SIZE:
        raise ValueError(f"initramfs LZMA {len(compressed_rootfs)} exceeds slot {INNER_SLOT_SIZE}")

    decoder = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    verified_rootfs = decoder.decompress(compressed_rootfs)
    if verified_rootfs != new_rootfs or not decoder.eof:
        raise AssertionError("inner rootfs verification failed")

    inner_slot = compressed_rootfs + b"\x00" * (INNER_SLOT_SIZE - len(compressed_rootfs))
    patched_kernel = kernel[:INNER_OFFSET] + inner_slot + kernel_tail
    if len(patched_kernel) != len(kernel):
        raise AssertionError("kernel length changed")

    outer = compress_lzma_sdk(patched_kernel, 25)
    uimage = build_uimage(header, outer)
    if len(uimage) > PAYLOAD_OFFSET:
        raise ValueError(f"new uImage ends at 0x{len(uimage):X}, payload offset is 0x{PAYLOAD_OFFSET:X}")

    output = bytearray(b"\xFF" * len(base))
    output[:len(uimage)] = uimage
    output[PAYLOAD_OFFSET:PAYLOAD_OFFSET + len(driver_payload)] = driver_payload
    if len(output) != MTD4_SIZE:
        raise AssertionError("output mtd4 length changed")

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

    names = {entry.name for entry in new_entries}
    for required in ("bin/endoscope-connectivity", EXTRACTOR_PATH, MONITOR_HELPER_PATH, RTAPCAP_PATH, AIRODUMP_PATH, AIREPLAY_PATH, AIRTOOLS_PATH, AIRWIFI_PATH, README_PATH):
        if required not in names:
            raise AssertionError(f"missing rootfs path: {required}")
    rc_files = {entry.name: entry.data for entry in new_entries if entry.name in ("etc_ro/rcS", "sbin/wifi_ap.sh")}
    boot_text = b"\n".join(rc_files.values())
    if b"/bin/airtools </dev/null >/dev/null 2>&1" not in boot_text:
        raise AssertionError("wifi_ap.sh does not start airtools supervisor from dhcp_init")
    if b"WN723N airtools supervisor autostart" in rc_files.get("etc_ro/rcS", b""):
        raise AssertionError("rcS still contains old airtools autostart")
    wifi_ap = next(entry.data for entry in new_entries if entry.name == "sbin/wifi_ap.sh")
    if b'ap_name="AT"' not in wifi_ap:
        raise AssertionError("wifi management SSID is not patched to AT")
    if b'ap_password="12345678"' not in wifi_ap:
        raise AssertionError("wifi management password default is not patched to 12345678")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_MTD4.write_bytes(output)

    print(f"base={BASE_MTD4}")
    print(f"base_sha256={hashlib.sha256(base).hexdigest()}")
    print(f"output={OUTPUT_MTD4}")
    print(f"bytes={len(output)}")
    print(f"sha256={hashlib.sha256(output).hexdigest()}")
    print(f"old_rootfs_bytes={len(old_rootfs)}")
    print(f"new_rootfs_bytes={len(new_rootfs)}")
    print(f"inner_lzma_bytes={len(compressed_rootfs)}")
    print(f"inner_slot_bytes={INNER_SLOT_SIZE}")
    print(f"inner_zero_padding={INNER_SLOT_SIZE - len(compressed_rootfs)}")
    print(f"uimage_bytes={len(uimage)}")
    print(f"payload_offset=0x{PAYLOAD_OFFSET:X}")
    print(f"payload_bytes={len(driver_payload)}")
    print(f"payload_sha256={hashlib.sha256(driver_payload).hexdigest()}")
    print(f"driver_ko_bytes={DRIVER_KO.stat().st_size}")
    print(f"driver_ko_sha256={hashlib.sha256(DRIVER_KO.read_bytes()).hexdigest()}")
    print(f"extractor_bytes={EXTRACTOR.stat().st_size}")
    print(f"extractor_sha256={hashlib.sha256(EXTRACTOR.read_bytes()).hexdigest()}")
    print(f"rtapcap_bytes={RTAPCAP.stat().st_size}")
    print(f"rtapcap_sha256={hashlib.sha256(RTAPCAP.read_bytes()).hexdigest()}")
    print(f"airodump_bytes={AIRODUMP.stat().st_size}")
    print(f"airodump_sha256={hashlib.sha256(AIRODUMP.read_bytes()).hexdigest()}")
    print(f"aireplay_bytes={AIREPLAY.stat().st_size}")
    print(f"aireplay_sha256={hashlib.sha256(AIREPLAY.read_bytes()).hexdigest()}")
    print(f"airtools_bytes={AIRTOOLS.stat().st_size}")
    print(f"airtools_sha256={hashlib.sha256(AIRTOOLS.read_bytes()).hexdigest()}")
    print("autoload=enabled_airtools_supervisor_from_wifi_ap_dhcp_init")
    print("management_ssid=AT")
    print("management_password_default=12345678")
    print(f"airwifi_bytes={len(AIRWIFI.encode('utf-8'))}")
    print(f"airwifi_sha256={hashlib.sha256(AIRWIFI.encode('utf-8')).hexdigest()}")


if __name__ == "__main__":
    main()
