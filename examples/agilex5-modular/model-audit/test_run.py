import importlib.util
import unittest
from pathlib import Path


RUNNER = Path(__file__).with_name("run.py")
spec = importlib.util.spec_from_file_location("pio_runner", RUNNER)
pio_runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(pio_runner)


def passing_uart(negative=False):
    lines = [
        "PIO_AUDIT_BEGIN",
        "BUTTON_DATA=0x0000000000000000",
        "DIPSW_DATA=0x0000000000000000",
        "SYSID_DATA=0x0000000000000000",
        "PASS BUTTON_INPUT stable, field=bit0",
        "PASS DIPSW_INPUT stable, field=bit0",
        "PASS SYSID 64-bit read stable",
        "LED_DATA_SAVED=0x0000000000000000",
        "LED_READBACK_A=0x00000000a55aa55b",
        "PASS LED pattern A readback",
        "LED_READBACK_B=0x000000005aa55aa5",
        "PASS LED pattern B readback",
    ]
    if negative:
        lines.extend(
            [
                "PASS negative control known-good LED write",
                "PASS PIO_NEGATIVE bad expected mask rejected",
            ]
        )
    lines.extend(["PASS LED original value restored", "PIO_AUDIT_COMPLETE status=0"])
    return "\n".join(lines) + "\n"


class PioAssessorTests(unittest.TestCase):
    def test_positive_case_passes(self):
        self.assertTrue(
            pio_runner.check_result("pio", 0, "PIO_AUDIT_DDR_READY", passing_uart())
        )

    def test_expected_mask_negative_control_passes(self):
        self.assertTrue(
            pio_runner.check_result(
                "mask-negative", 0, "PIO_AUDIT_DDR_READY", passing_uart(negative=True)
            )
        )

    def test_negative_case_requires_expected_rejection_marker(self):
        self.assertFalse(
            pio_runner.check_result(
                "mask-negative", 0, "PIO_AUDIT_DDR_READY", passing_uart()
            )
        )

    def test_rejects_conflicting_completion_statuses(self):
        uart = passing_uart() + "PIO_AUDIT_COMPLETE status=1\n"
        self.assertFalse(pio_runner.check_result("pio", 0, "PIO_AUDIT_DDR_READY", uart))

    def test_rejects_missing_ddr_bootstrap_marker(self):
        self.assertFalse(pio_runner.check_result("pio", 0, "", passing_uart()))

    def test_rejects_simulator_failure(self):
        self.assertFalse(
            pio_runner.check_result("pio", 1, "PIO_AUDIT_DDR_READY", passing_uart())
        )


if __name__ == "__main__":
    unittest.main()
