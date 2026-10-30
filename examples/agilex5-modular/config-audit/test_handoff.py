import importlib.util
import json
import contextlib
import io
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("handoff.py")
spec = importlib.util.spec_from_file_location("handoff", SCRIPT)
handoff = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(handoff)


def make_handoff() -> bytes:
    data = bytearray(0x424)
    data[0:4] = b"BOOT"
    data[0x10:0x14] = b"PMUX"
    data[0x1A0:0x1A4] = b"IOCT"
    data[0x330:0x334] = b"FPGA"

    pmux_pairs = [(offset, offset ^ 0x5A) for offset in range(0, 0xC0, 4)]
    pmux_pairs[2] = (0x08, 0x04)
    pmux_pairs[3] = (0x0C, 0x08)
    for i, pair in enumerate(pmux_pairs):
        handoff.struct.pack_into(">II", data, 0x20 + i * 8, *pair)

    fpga_pairs = [(offset, 0) for offset in range(0, 0x50, 4)]
    fpga_pairs[14] = (0x38, 0)
    for i, pair in enumerate(fpga_pairs):
        handoff.struct.pack_into(">II", data, 0x340 + i * 8, *pair)
    return bytes(data)


class ParseHandoffTests(unittest.TestCase):
    def test_extracts_expected_offsets(self):
        self.assertEqual(
            handoff.parse_handoff(make_handoff()),
            {"PIN2SEL": 0x04, "PIN3SEL": 0x08, "UART0_USEFPGA": 0},
        )

    def test_rejects_corrupted_boot_magic(self):
        data = bytearray(make_handoff())
        data[0] = ord("X")
        with self.assertRaisesRegex(handoff.InvalidInput, "BOOT magic"):
            handoff.parse_handoff(bytes(data))

    def test_rejects_truncated_handoff(self):
        with self.assertRaisesRegex(handoff.InvalidInput, "truncated FPGA array"):
            handoff.parse_handoff(make_handoff()[:0x3D8])

    def test_rejects_duplicate_pmux_offset(self):
        data = bytearray(make_handoff())
        handoff.struct.pack_into(">I", data, 0x20 + 4 * 8, 0x08)
        with self.assertRaisesRegex(handoff.InvalidInput, "duplicate PMUX"):
            handoff.parse_handoff(bytes(data))

    def test_rejects_missing_target_offset(self):
        data = bytearray(make_handoff())
        handoff.struct.pack_into(">I", data, 0x20 + 2 * 8, 0x0A)
        with self.assertRaisesRegex(handoff.InvalidInput, "missing PMUX register"):
            handoff.parse_handoff(bytes(data))

    def test_compare_reports_register_mismatch_and_handoff_hash(self):
        blob = make_handoff()
        result = handoff.compare(
            blob,
            {"PIN2SEL": 0x04, "PIN3SEL": 0x09, "UART0_USEFPGA": 0},
        )
        self.assertEqual(result["status"], "mismatch")
        self.assertEqual(result["checks"]["PIN3SEL"]["expected"], 0x08)
        self.assertEqual(result["checks"]["PIN3SEL"]["actual"], 0x09)
        self.assertEqual(len(result["handoff_sha256"]), 64)

    def test_cli_returns_two_for_invalid_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            blob_path = root / "handoff.bin"
            snapshot_path = root / "snapshot.json"
            blob_path.write_bytes(make_handoff())
            snapshot_path.write_text(json.dumps({"registers": {}}), encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                result = handoff.main(
                    ["--handoff", str(blob_path), "--snapshot", str(snapshot_path)]
                )
            self.assertEqual(result, 2)
            self.assertEqual(json.loads(output.getvalue())["status"], "invalid_input")


if __name__ == "__main__":
    unittest.main()
