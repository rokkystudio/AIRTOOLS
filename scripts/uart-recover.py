#!/usr/bin/env python3
"""
UART recovery for the ENDOSCOPE MT7628 U-Boot.

Workflow:
  1. Run the mandatory mtd4 preflight.
  2. Open COM3 at 57600 8N1 without flow control.
  3. Wait for a *cold* boot and repeatedly select U-Boot menu item 0.
  4. Wait until U-Boot announces Kermit binary receive mode.
  5. Send the verified mtd4 with a minimal Kermit sender compatible with
     U-Boot's loadb receiver.
  6. Keep monitoring UART while U-Boot writes the image to SPI flash.

The script never writes anything unless --recover is explicitly supplied.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

import serial


ROOT = Path(r"D:\PROJECTS\ENDOSCOPE")
DEFAULT_IMAGE = ROOT / "dumps" / "modified" / "mtd4_connectivity.bin"
VERIFY_SCRIPT = ROOT / "services" / "connectivity" / "verify-mtd4.py"

BAUDRATE = 57600
SOH = 0x01
CR = 0x0D
SPACE = 0x20
QUOTE = 0x23
ACK = ord("Y")
NACK = ord("N")

MAX_LONG_PACKET = 9024
MAX_ENCODED_DATA = 9000


class RecoveryError(RuntimeError):
    """Raised when UART recovery cannot safely continue."""


def tochar(value: int) -> int:
    """Converts a Kermit 6-bit integer to its printable representation."""
    return (value + SPACE) & 0xFF


def untochar(value: int) -> int:
    """Converts a printable Kermit integer back to its numeric value."""
    return (value - SPACE) & 0xFF


def checksum1(data: bytes) -> int:
    """Returns the Kermit type-1 six-bit checksum."""
    total = sum(data)
    return (total + ((total >> 6) & 0x03)) & 0x3F


def encode_binary(data: bytes) -> bytes:
    """Applies the control quoting understood by U-Boot's loadb receiver."""
    encoded = bytearray()

    for value in data:
        if value == QUOTE:
            encoded.extend((QUOTE, QUOTE))
        elif value < 0x20:
            encoded.extend((QUOTE, value ^ 0x40))
        elif value == 0x7F:
            encoded.extend((QUOTE, 0x3F))
        else:
            encoded.append(value)

    return bytes(encoded)


def build_packet(sequence: int, packet_type: int, data: bytes = b"") -> bytes:
    """Builds one standard or long Kermit packet using type-1 checksums."""
    sequence &= 0x3F

    if len(data) + 3 <= 94:
        length = len(data) + 3
        body = bytearray(
            (
                tochar(length),
                tochar(sequence),
                packet_type,
            )
        )
        body.extend(data)
        body.append(tochar(checksum1(body)))
        return bytes((SOH,)) + bytes(body) + bytes((CR,))

    long_length = len(data) + 1
    if long_length > MAX_LONG_PACKET:
        raise RecoveryError(
            f"Kermit encoded packet is too large: {long_length} > {MAX_LONG_PACKET}"
        )

    high, low = divmod(long_length, 95)
    header = bytearray(
        (
            tochar(0),
            tochar(sequence),
            packet_type,
            tochar(high),
            tochar(low),
        )
    )
    header_check = tochar(checksum1(header))
    checksum_input = header + bytes((header_check,)) + data
    packet_check = tochar(checksum1(checksum_input))

    return (
        bytes((SOH,))
        + bytes(header)
        + bytes((header_check,))
        + data
        + bytes((packet_check, CR))
    )


def read_packet(port: serial.Serial, timeout: float) -> tuple[int, int, bytes]:
    """Reads and validates one Kermit response packet from U-Boot."""
    deadline = time.monotonic() + timeout

    while time.monotonic() < deadline:
        value = port.read(1)
        if not value:
            continue
        if value[0] == SOH:
            break
    else:
        raise RecoveryError("timeout waiting for Kermit response")

    first = read_exact(port, 1, deadline)[0]
    length = untochar(first)
    sequence = untochar(read_exact(port, 1, deadline)[0])
    packet_type = read_exact(port, 1, deadline)[0]

    checksum_data = bytearray((first, tochar(sequence), packet_type))

    if length == 0:
        length_high = read_exact(port, 1, deadline)[0]
        length_low = read_exact(port, 1, deadline)[0]
        checksum_data.extend((length_high, length_low))

        header_check = read_exact(port, 1, deadline)[0]
        expected_header = tochar(checksum1(checksum_data))
        if header_check != expected_header:
            raise RecoveryError("invalid Kermit long-packet header checksum")

        checksum_data.append(header_check)
        payload_length = untochar(length_high) * 95 + untochar(length_low) - 1
    else:
        payload_length = length - 3

    if payload_length < 0:
        raise RecoveryError("invalid Kermit response length")

    payload = read_exact(port, payload_length, deadline)
    checksum_data.extend(payload)

    packet_check = read_exact(port, 1, deadline)[0]
    expected_packet = tochar(checksum1(checksum_data))
    if packet_check != expected_packet:
        raise RecoveryError("invalid Kermit packet checksum")

    eol = read_exact(port, 1, deadline)[0]
    if eol != CR:
        raise RecoveryError(f"unexpected Kermit packet terminator 0x{eol:02X}")

    return sequence, packet_type, payload


def read_exact(port: serial.Serial, length: int, deadline: float) -> bytes:
    """Reads exactly length bytes before a monotonic deadline."""
    result = bytearray()

    while len(result) < length:
        if time.monotonic() >= deadline:
            raise RecoveryError(
                f"timeout reading Kermit packet: {len(result)}/{length} bytes"
            )
        chunk = port.read(length - len(result))
        if chunk:
            result.extend(chunk)

    return bytes(result)


def send_packet_with_retry(
    port: serial.Serial,
    sequence: int,
    packet_type: int,
    data: bytes = b"",
    retries: int = 12,
) -> bytes:
    """Sends one packet and retries until the matching U-Boot ACK is received."""
    packet = build_packet(sequence, packet_type, data)

    for attempt in range(1, retries + 1):
        port.write(packet)
        port.flush()

        try:
            response_sequence, response_type, response_data = read_packet(port, 6.0)
        except RecoveryError:
            if attempt == retries:
                raise
            continue

        if response_sequence != (sequence & 0x3F):
            if attempt == retries:
                raise RecoveryError(
                    f"unexpected ACK sequence {response_sequence}, "
                    f"expected {sequence & 0x3F}"
                )
            continue

        if response_type == ACK:
            return response_data

        if response_type == NACK:
            if attempt == retries:
                raise RecoveryError(f"U-Boot NACKed packet {sequence}")
            continue

        if attempt == retries:
            raise RecoveryError(
                f"unexpected Kermit response type 0x{response_type:02X}"
            )

    raise RecoveryError("unreachable Kermit retry state")


def send_kermit_file(port: serial.Serial, image: bytes, remote_name: str) -> None:
    """Sends an image using the subset of Kermit implemented by U-Boot loadb."""
    sequence = 0

    send_init = bytes(
        (
            tochar(94),
            tochar(5),
            tochar(0),
            0x40,
            tochar(CR),
            QUOTE,
            ord("N"),
            ord("1"),
            ord("N"),
            tochar(2),
            tochar(0),
            tochar(94),
            tochar(94),
        )
    )

    response = send_packet_with_retry(port, sequence, ord("S"), send_init)
    if len(response) >= 13:
        remote_long = untochar(response[11]) * 95 + untochar(response[12])
        if remote_long < MAX_LONG_PACKET:
            raise RecoveryError(
                f"U-Boot negotiated long packet {remote_long}, expected at least "
                f"{MAX_LONG_PACKET}"
            )

    sequence = (sequence + 1) & 0x3F
    send_packet_with_retry(
        port,
        sequence,
        ord("F"),
        encode_binary(remote_name.encode("ascii", "strict")),
    )

    sequence = (sequence + 1) & 0x3F
    offset = 0
    total = len(image)
    last_report = -1

    while offset < total:
        raw_end = min(offset + 8192, total)

        while True:
            encoded = encode_binary(image[offset:raw_end])
            if len(encoded) <= MAX_ENCODED_DATA:
                break
            raw_end -= max(1, (len(encoded) - MAX_ENCODED_DATA + 1) // 2)

        if raw_end <= offset:
            raise RecoveryError("could not fit binary data into a Kermit packet")

        send_packet_with_retry(port, sequence, ord("D"), encoded)
        offset = raw_end
        sequence = (sequence + 1) & 0x3F

        percent = (offset * 100) // total
        if percent != last_report and (percent % 5 == 0 or offset == total):
            print(f"Kermit transfer: {percent}% ({offset}/{total} bytes)", flush=True)
            last_report = percent

    send_packet_with_retry(port, sequence, ord("Z"))
    sequence = (sequence + 1) & 0x3F
    send_packet_with_retry(port, sequence, ord("B"))

    print(f"Kermit transfer complete: {total} bytes", flush=True)


def load_verifier():
    """Loads verify-mtd4.py as a module without duplicating firmware checks."""
    spec = importlib.util.spec_from_file_location("endoscope_verify_mtd4", VERIFY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RecoveryError(f"cannot load verifier: {VERIFY_SCRIPT}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def preflight(image: Path) -> None:
    """Runs the same mandatory checks used by build-firmware.bat."""
    verifier = load_verifier()
    try:
        verifier.verify_modified(image)
    except Exception as exc:
        raise RecoveryError(f"firmware preflight failed: {exc}") from exc


def wait_for_serial_recovery(
    port: serial.Serial,
    timeout: float,
) -> None:
    """Selects U-Boot menu item 0 during a cold boot and waits for loadb."""
    deadline = time.monotonic() + timeout
    buffer = bytearray()
    selected = False
    software_resets = 0

    print(
        "UART recovery armed. Power-cycle the ENDOSCOPE now "
        "(remove power, wait a few seconds, reconnect power).",
        flush=True,
    )

    while time.monotonic() < deadline:
        chunk = port.read(4096)
        if chunk:
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            buffer.extend(chunk)
            if len(buffer) > 32768:
                del buffer[:-32768]

            if b"Software System Reset Occurred" in chunk:
                software_resets += 1

            tail = bytes(buffer)

            if (
                b"Please choose the operation" in tail
                or b"RESET MT7628 PHY!!!!!!" in tail
                or b"estimate memory size =64 Mbytes" in tail
            ):
                for _ in range(32):
                    port.write(b"0")
                    port.flush()
                    time.sleep(0.015)
                selected = True

            if (
                b"System Load Linux then write to Flash via Serial" in tail
                or b"Ready for binary (kermit) download" in tail
            ):
                if b"Ready for binary (kermit) download" not in tail:
                    ready_deadline = time.monotonic() + 8
                    while time.monotonic() < ready_deadline:
                        more = port.read(4096)
                        if more:
                            sys.stdout.buffer.write(more)
                            sys.stdout.buffer.flush()
                            buffer.extend(more)
                            if b"Ready for binary (kermit) download" in buffer:
                                break

                if b"Ready for binary (kermit) download" not in buffer:
                    raise RecoveryError(
                        "U-Boot selected serial recovery but did not enter loadb"
                    )

                port.reset_input_buffer()
                print("\nU-Boot Kermit receiver is ready.", flush=True)
                return

    if not selected and software_resets:
        raise RecoveryError(
            "only software-reset boot loops were observed. "
            "A real power-cycle is required."
        )

    raise RecoveryError(
        "did not reach U-Boot serial recovery. "
        "Check CP2102 TXD -> board R, GND, COM port, and perform a cold power-cycle."
    )


def monitor_flash(port: serial.Serial, timeout: float = 120.0) -> str:
    """Monitors U-Boot output after transfer and returns the captured text."""
    deadline = time.monotonic() + timeout
    output = bytearray()
    quiet_deadline = None

    while time.monotonic() < deadline:
        chunk = port.read(4096)
        if chunk:
            output.extend(chunk)
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
            quiet_deadline = time.monotonic() + 5

            if (
                b"System Boot system code via Flash" in output
                or b"Uncompressing Kernel Image" in output
                or b"U-Boot 1.1.3" in output[-4096:]
            ):
                if len(output) > 256:
                    break
        elif quiet_deadline is not None and time.monotonic() >= quiet_deadline:
            break

    return output.decode("latin1", "replace")


def main() -> None:
    """Validates arguments and executes an explicitly armed UART recovery."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="COM3")
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument(
        "--recover",
        action="store_true",
        help="explicitly allow U-Boot serial recovery and flash write",
    )
    parser.add_argument("--wait", type=float, default=120.0)
    args = parser.parse_args()

    image_path = args.image.resolve()

    print(f"Preflight: {image_path}", flush=True)
    preflight(image_path)

    if not args.recover:
        print(
            "Preflight passed. No write performed. "
            "Run again with --recover to arm UART recovery.",
            flush=True,
        )
        return

    image = image_path.read_bytes()

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

        wait_for_serial_recovery(port, args.wait)
        send_kermit_file(port, image, image_path.name)

        print("Monitoring U-Boot flash operation...", flush=True)
        output = monitor_flash(port)

    if "LZMA ERROR" in output:
        raise RecoveryError("U-Boot reported an LZMA error after recovery")

    print("UART recovery transfer finished.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RecoveryError, serial.SerialException) as exc:
        print(f"RECOVERY FAILED: {exc}", file=sys.stderr, flush=True)
        raise SystemExit(1)
