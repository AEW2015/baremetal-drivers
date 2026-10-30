#!/usr/bin/env python3
"""Run the modeled Agilex 5 LWHPS2FPGA PIO lesson in Simics."""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "simics"))
from support import PROJECT, digest, new_run, execute, save

CASES = ("pio", "mask-negative")


def make_script(image, boot):
    quote = json.dumps
    return f'''$fsbl_image_filename = {quote(str(boot))}
$hps_reset_vector = 0
run-script (sim->project + "/targets/agilex5e-universal/agilex5e-universal.simics")
$con = $system.board.fpga.soc_inst.hps_subsys.agilex_hps.console0.con
$ready = (bp.console_string.break $con "SoCFPGA Bare-Metal > ")
$done = (bp.console_string.break $con -regexp "PIO_AUDIT_COMPLETE status=[01]")
$con.record-start
script-branch {{
 run
 bp.wait-for-breakpoint $ready
 stop
 $con.input "ddr_selftest\\n"
 run
 bp.wait-for-breakpoint $ready
 stop
 echo "PIO_AUDIT_DDR_READY"
 hps.phys_mem.load-file {quote(str(image))} 0x82100000
 pselect "system.board.fpga.soc_inst.hps_subsys.agilex_hps.core[0]"
 set-pc 0x82100000
 run
 bp.wait-for-breakpoint $done
 stop
 $transcript = ($con.record-stop)
 echo "UART_RECORD_BEGIN"
 echo $transcript
 echo "UART_RECORD_END"
 exit 0
}}
'''


def extract_uart(body):
    match = re.search(r"UART_RECORD_BEGIN\n(.*?)UART_RECORD_END", body, re.S)
    return match[1].replace("\r", "") if match else ""


def check_result(name, code, body, uart):
    completion = re.findall(r"^PIO_AUDIT_COMPLETE status=([01])$", uart, re.M)
    required = [
        "PIO_AUDIT_BEGIN",
        "BUTTON_DATA=",
        "DIPSW_DATA=",
        "SYSID_DATA=",
        "PASS BUTTON_INPUT stable, field=bit0",
        "PASS DIPSW_INPUT stable, field=bit0",
        "PASS SYSID 64-bit read stable",
        "PASS LED pattern A readback",
        "PASS LED pattern B readback",
        "PASS LED original value restored",
        "PIO_AUDIT_COMPLETE status=0",
    ]
    if name == "mask-negative":
        required.extend(
            [
                "PASS negative control known-good LED write",
                "PASS PIO_NEGATIVE bad expected mask rejected",
            ]
        )
    return (
        code == 0
        and "PIO_AUDIT_DDR_READY" in body
        and completion == ["0"]
        and all(item in uart for item in required)
        and "FAIL " not in uart
        and "DDR stage skipped" not in uart
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", default=",".join(CASES), help="Comma-separated: " + ",".join(CASES))
    parser.add_argument("--project", type=Path, default=PROJECT, help="Deployed Simics project directory")
    parser.add_argument("--boot", type=Path, default=ROOT / "build" / "upstream26-ocram" / "baremetal.bin")
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()
    names = args.only.split(",")
    if not names or any(name not in CASES for name in names):
        parser.error("Choose " + ",".join(CASES))
    if not 1 <= args.timeout <= 300:
        parser.error("timeout must be 1..300 seconds")
    if not args.boot.is_file():
        parser.error("Build the OCRAM bootstrap first or pass --boot")

    build = ROOT / "build" / "model-audit"
    metadata = json.loads((build / "build.json").read_text())
    for path, expected in metadata["source_sha256"].items():
        if digest(ROOT / path) != expected:
            raise RuntimeError("Build source changed; rerun ./model-audit/build.sh: " + path)
    for filename, expected in metadata["artifacts"].items():
        if digest(build / filename) != expected:
            raise RuntimeError("Build artifact hash mismatch: " + filename)

    out = new_run("model-audit-pio")
    model_info = ROOT / "model-audit" / "model-register-info.txt"
    record = {
        "scope": "Simics model PIO readback; no physical board or external button/switch transition qualification",
        "project": str(args.project.resolve()),
        "bootstrap_sha256": digest(args.boot),
        "runner_sha256": digest(Path(__file__)),
        "build": metadata,
        "model_register_info_sha256": digest(model_info),
        "register_map": {
            "lwhps2fpga_base": "0x20000000",
            "sysid": {"address": "0x20010000", "size": "0x8", "access": "read"},
            "button_data": {"address": "0x20010060", "width_bits": 32, "input_mask": "0x00000001"},
            "dipsw_data": {"address": "0x20010070", "width_bits": 32, "input_mask": "0x00000001"},
            "led_data": {"address": "0x20010080", "width_bits": 32, "output_mask": "0xffffffff"},
        },
        "tests": [],
    }
    for name in names:
        image = build / (name + ".bin")
        folder = out / name
        folder.mkdir()
        test_script = folder / "test.simics"
        test_script.write_text(make_script(image.resolve(), args.boot.resolve()))
        code, seconds, body = execute(args.project, test_script, folder / "terminal.log", args.timeout)
        uart = extract_uart(body)
        (folder / "uart.txt").write_text(uart)
        passed = check_result(name, code, body, uart)
        record["tests"].append(
            {
                "name": name,
                "status": "pass" if passed else "timeout" if code == 124 else "fail",
                "simulator_exit": code,
                "seconds": round(seconds, 3),
                "binary_sha256": digest(image),
                "script_sha256": digest(test_script),
                "uart_sha256": digest(folder / "uart.txt"),
            }
        )
        save(out, record)
        print(("PASS " if passed else "FAIL ") + name, flush=True)
        if not passed:
            print(body[-3000:], flush=True)
    return int(any(test["status"] != "pass" for test in record["tests"]))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, ValueError) as exc:
        print("ERROR: " + str(exc), file=sys.stderr)
        raise SystemExit(1)
