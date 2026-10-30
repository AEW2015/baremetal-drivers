#!/usr/bin/env python3
"""Compare selected pinmux handoff values with a captured register snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any


BOOT_MAGIC = b"BOOT"
PMUX_MAGIC = b"PMUX"
IOCT_MAGIC = b"IOCT"
FPGA_MAGIC = b"FPGA"

PMUX_HEADER = 0x10
PMUX_ARRAY = 0x20
PMUX_PAIR_COUNT = 48
IOCT_HEADER = 0x1A0
FPGA_HEADER = 0x330
FPGA_ARRAY = 0x340
FPGA_PAIR_COUNT = 20

TARGETS = {
    "PIN2SEL": (PMUX_ARRAY, 0x08),
    "PIN3SEL": (PMUX_ARRAY, 0x0C),
    "UART0_USEFPGA": (FPGA_ARRAY, 0x38),
}


class InvalidInput(ValueError):
    """Raised when an input file does not follow the expected format."""


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise InvalidInput(f"truncated handoff at byte offset 0x{offset:x}")
    return struct.unpack_from(">I", data, offset)[0]


def _check_magic(data: bytes, offset: int, expected: bytes, section: str) -> None:
    end = offset + len(expected)
    if end > len(data):
        raise InvalidInput(f"truncated {section} header at byte offset 0x{offset:x}")
    actual = data[offset:end]
    if actual != expected:
        raise InvalidInput(
            f"invalid {section} magic at byte offset 0x{offset:x}: "
            f"expected {expected.decode('ascii')}, got {actual!r}"
        )


def _read_pairs(data: bytes, array_offset: int, pair_count: int, section: str) -> dict[int, int]:
    end = array_offset + pair_count * 8
    if end > len(data):
        raise InvalidInput(
            f"truncated {section} array: need bytes through 0x{end:x}, "
            f"handoff has 0x{len(data):x} bytes"
        )
    pairs: dict[int, int] = {}
    for index in range(pair_count):
        offset = _u32(data, array_offset + index * 8)
        value = _u32(data, array_offset + index * 8 + 4)
        if offset in pairs:
            raise InvalidInput(f"duplicate {section} register offset 0x{offset:x}")
        pairs[offset] = value
    return pairs


def parse_handoff(data: bytes) -> dict[str, int]:
    """Extract audited register expectations from a big-endian HOFF blob."""
    _check_magic(data, 0, BOOT_MAGIC, "BOOT")
    _check_magic(data, PMUX_HEADER, PMUX_MAGIC, "PMUX")
    _check_magic(data, IOCT_HEADER, IOCT_MAGIC, "IOCT")
    _check_magic(data, FPGA_HEADER, FPGA_MAGIC, "FPGA")

    pmux = _read_pairs(data, PMUX_ARRAY, PMUX_PAIR_COUNT, "PMUX")
    fpga = _read_pairs(data, FPGA_ARRAY, FPGA_PAIR_COUNT, "FPGA")
    result: dict[str, int] = {}
    for name, (array_offset, register_offset) in TARGETS.items():
        table = pmux if array_offset == PMUX_ARRAY else fpga
        if register_offset not in table:
            section = "PMUX" if table is pmux else "FPGA"
            raise InvalidInput(
                f"missing {section} register offset 0x{register_offset:x} for {name}"
            )
        result[name] = table[register_offset]
    return result


def load_snapshot(path: Path) -> dict[str, int]:
    try:
        document: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InvalidInput(f"cannot read snapshot JSON: {exc}") from exc
    if not isinstance(document, dict) or not isinstance(document.get("registers"), dict):
        raise InvalidInput("snapshot must contain a 'registers' object")

    registers = document["registers"]
    result: dict[str, int] = {}
    for name in TARGETS:
        if name not in registers:
            raise InvalidInput(f"snapshot is missing register {name}")
        value = registers[name]
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
            raise InvalidInput(f"snapshot register {name} must be an unsigned 32-bit integer")
        result[name] = value
    return result


def compare(handoff: bytes, snapshot: dict[str, int]) -> dict[str, Any]:
    expected = parse_handoff(handoff)
    checks = {
        name: {
            "expected": expected[name],
            "actual": snapshot[name],
            "status": "match" if expected[name] == snapshot[name] else "mismatch",
        }
        for name in TARGETS
    }
    return {
        "status": "match" if all(c["status"] == "match" for c in checks.values()) else "mismatch",
        "handoff_sha256": hashlib.sha256(handoff).hexdigest(),
        "checks": checks,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--handoff", required=True, type=Path, help="HPS bootloader handoff binary")
    parser.add_argument("--snapshot", required=True, type=Path, help="JSON register snapshot")
    args = parser.parse_args(argv)

    try:
        handoff = args.handoff.read_bytes()
        snapshot = load_snapshot(args.snapshot)
        report = compare(handoff, snapshot)
    except (OSError, InvalidInput) as exc:
        print(json.dumps({"status": "invalid_input", "error": str(exc)}, sort_keys=True))
        return 2

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "match" else 1


if __name__ == "__main__":
    sys.exit(main())
