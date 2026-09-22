#!/usr/bin/env python3
"""
RAM-only test boot for the ENDOSCOPE MT7628 U-Boot.

This is the mandatory first step before any future persistent mtd4 write:
  1. Verify the selected image on the PC.
  2. Enter U-Boot CLI during a real cold boot.
  3. Upload only the uImage portion to RAM at 0x81000000 via Kermit.
  4. Run bootm from RAM.

No SPI flash write command is issued by this script.

For recovery, boot the preserved factory image from RAM first:
  python scripts\\uart\\test-boot.py --image dumps\\original\\mtd4_kernel.bin --boot

For testing a modified image before flashing:
  python scripts\\uart\\test-boot.py --image dumps\\modified\\mtd4_connectivity.bin --boot
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import struct
import sys
import time
from pathlib import Path

import serial


ROOT = Path(r"D:\PROJECTS\AIRTOOLS")
ORIGINAL = ROOT / "dumps" / "original" / "mtd4_kernel.bin"
MODIFIED = ROOT / "dumps" / "modified" / "mtd4_connectivity.bin"
VERIFY_SCRIPT = ROOT / "src" / "connectivity" / "verify-mtd4.py"
RECOVERY_SCRIPT = ROOT / "scripts" / "uart" / "recover.py"

ORIGINAL_SHA256 = "72904FD990D724D81CF2EBD3C1E812954C55422442D16CAB7C0E152FF3610C2D"
BAUDRATE = 57600
LOAD_ADDRESS = 0x81000000


class TestBootError(RuntimeError):
    """Raised when a safe RAM-only boot cannot continue."""


def load_module(path: Path, name: str):
    """Loads a local Python helper module by path."""
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise TestBootError(f"cannot load helper module: {path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify_image(image_path: Path) -> bytes:
    """Verifies original or modified mtd4 and returns only its uImage bytes."""
    verifier = load_module(VERIFY_SCRIPT, "endoscope_verify_mtd4")
    image = image_path.read_bytes()

    if image_path.resolve() == ORIGINAL.resolve():
        digest = hashlib.sha256(image).hexdigest().upper()
        if digest != ORIGINAL_SHA256:
            raise TestBootError(
                f"factory mtd4 SHA256 mismatch: {digest}, expected {ORIGINAL_SHA256}"
            )

        header, outer, kernel = verifier.parse_uimage(image, "original")
        verifier.legacy_decode(outer, kernel, "original outer LZMA")
        rootfs, inner, _ = verifier.extract_inner(kernel, "original")
        verifier.legacy_decode(inner, rootfs, "original inner LZMA")
        print("FACTORY PREFLIGHT OK", flush=True)
    else:
        try:
            verifier.verify_modified(image_path)
        except Exception as exc:
            raise TestBootError(f"modified firmware preflight failed: {exc}") from exc

    if len(image) < 64:
        raise TestBootError("image is shorter than a uImage header")

    payload_size = struct.unpack_from(">I", image, 12)[0]
    uimage_size = 64 + payload_size

    if uimage_size > len(image):
        raise TestBootError(
            f"uImage size {uimage_size} exceeds partition image size {len(image)}"
        )

    uimage = image[:uimage_size]
    print(f"uImage bytes: {len(uimage)}", flush=True)
    print(
        f"uImage SHA256: {hashlib.sha256(uimage).hexdigest().upper()}",
        flush=True,
    )
    return uimage


def wait_for_uboot_cli(port: serial.Serial, timeout: float) -> None:
    """Continuously sends ESC+4 from port-open until the MT7628 U-Boot CLI appears."""
    deadline = time.monotonic() + timeout
    buffer = bytearray()
    next_tx = 0.0

    old_timeout = port.timeout
    port.timeout = 0.001

    print(
        "RAM test boot armed. Sending ESC+4 continuously from port-open.",
        flush=True,
    )

    try:
        while time.monotonic() < deadline:
            now = time.monotonic()

            if now >= next_tx:
                port.write(b"\x1b4")
                port.flush()
                next_tx = now + 0.003

            chunk = port.read(256)
            if chunk:
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                buffer.extend(chunk)

                if len(buffer) > 65536:
                    del buffer[:-65536]

                tail = bytes(buffer[-16384:])

                if b"Please choose the operation" in tail:
                    for _ in range(8):
                        port.write(b"4")
                        port.flush()
                        time.sleep(0.005)

                if b"MT7628 #" in tail:
                    port.write(b"\x03\r")
                    port.flush()
                    time.sleep(0.15)
                    port.reset_input_buffer()
                    print("\nU-Boot CLI acquired.", flush=True)
                    return

            time.sleep(0.0005)
    finally:
        port.timeout = old_timeout

    raise TestBootError(
        "U-Boot CLI was not acquired. ESC+4 was sent continuously from port-open. "
        "If this persists, use a scope/multimeter on the board RX pad or SPI recovery."
    )

def wait_for_text(
    port: serial.Serial,
    needles: tuple[bytes, ...],
    timeout: float,
    echo: bool = True,
) -> bytes:
    """Reads UART until any requested marker appears or timeout expires."""
    deadline = time.monotonic() + timeout
    buffer = bytearray()

    while time.monotonic() < deadline:
        chunk = port.read(4096)
        if not chunk:
            continue

        buffer.extend(chunk)
        if echo:
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()

        if any(needle in buffer for needle in needles):
            return bytes(buffer)

        if len(buffer) > 262144:
            del buffer[:-131072]

    wanted = ", ".join(repr(value) for value in needles)
    raise TestBootError(f"timeout waiting for UART markers: {wanted}")


def command(port: serial.Serial, text: str) -> None:
    """Sends one CR-terminated U-Boot command."""
    port.write(text.encode("ascii") + b"\r")
    port.flush()


def upload_to_ram(
    port: serial.Serial,
    recovery,
    uimage: bytes,
    remote_name: str,
) -> None:
    """Starts U-Boot loadb and uploads the verified uImage to RAM."""
    command(port, f"loadb {LOAD_ADDRESS:08x} {BAUDRATE}")

    wait_for_text(
        port,
        (b"Ready for binary (kermit) download",),
        10.0,
    )

    port.reset_input_buffer()
    recovery.send_kermit_file(port, uimage, remote_name)

    transfer_output = wait_for_text(
        port,
        (b"## Total Size", b"MT7628 #"),
        12.0,
    )

    if b"## Total Size" not in transfer_output:
        raise TestBootError("U-Boot did not report a completed Kermit transfer")

    if b"MT7628 #" not in transfer_output:
        wait_for_text(port, (b"MT7628 #",), 5.0)


def ram_boot(port: serial.Serial) -> bytes:
    """Runs bootm on the RAM image and monitors its boot output."""
    port.reset_input_buffer()
    command(port, f"bootm {LOAD_ADDRESS:08x}")

    output = wait_for_text(
        port,
        (
            b"starting pid",
            b"tty '/dev/ttyS1': '/bin/sh'",
            b"BusyBox",
            b"LZMA ERROR",
            b"Bad Magic Number",
            b"Bad Data CRC",
        ),
        60.0,
    )

    if b"LZMA ERROR" in output:
        raise TestBootError("U-Boot reported LZMA ERROR during RAM boot")
    if b"Bad Magic Number" in output:
        raise TestBootError("U-Boot rejected the RAM uImage magic")
    if b"Bad Data CRC" in output:
        raise TestBootError("U-Boot rejected the RAM uImage CRC")

    print("\nRAM BOOT REACHED LINUX.", flush=True)
    return output


def main() -> None:
    """Runs preflight and optionally performs a flash-free U-Boot RAM boot."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--image", type=Path, default=MODIFIED)
    parser.add_argument(
        "--boot",
        action="store_true",
        help="explicitly arm cold-boot UART interaction and RAM-only boot",
    )
    parser.add_argument("--wait", type=float, default=120.0)
    args = parser.parse_args()

    image_path = args.image.resolve()
    if not image_path.is_file():
        raise TestBootError(f"firmware image not found: {image_path}")

    print(f"Preflight: {image_path}", flush=True)
    uimage = verify_image(image_path)

    if not args.boot:
        print(
            "Preflight passed. No UART command and no flash write performed. "
            "Run with --boot for a RAM-only test boot.",
            flush=True,
        )
        return

    recovery = load_module(RECOVERY_SCRIPT, "endoscope_uart_recovery")

    with serial.Serial(
        args.port,
        BAUDRATE,
        bytesize=serial.EIGHTBITS,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        timeout=0.05,
        write_timeout=5,
        xonxoff=False,
        rtscts=False,
        dsrdtr=False,
    ) as port:
        port.reset_input_buffer()
        port.reset_output_buffer()

        wait_for_uboot_cli(port, args.wait)
        upload_to_ram(port, recovery, uimage, image_path.name)
        ram_boot(port)

    print(
        "RAM-only boot test finished. SPI flash was not modified.",
        flush=True,
    )


if __name__ == "__main__":
    try:
        main()
    except (TestBootError, serial.SerialException) as exc:
        print(f"RAM TEST BOOT FAILED: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
