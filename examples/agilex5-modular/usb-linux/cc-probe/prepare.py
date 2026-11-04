#!/usr/bin/env python3
# SPDX-License-Identifier: MIT-0
"""Create an isolated diagnostic copy of the bench's qualified 26.3 platform."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--enable-mode-writes', action='store_true', help='Explicit variant allowing only TI General-Control mode values; defaults to read-only')
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if output.exists() or source == output or source in output.parents:
        parser.error('Output must be a new directory outside the source platform')
    top = (source / 'baseline_a55.sv').read_text()
    qsf = (source / 'baseline_a55.qsf').read_text()
    if 'DEVICE A5ED065BB32AE6SR0' not in qsf or '26.3.0 Pro Edition' not in qsf:
        parser.error('Requires the matching Modular ES 26.3 platform; no production/Premium substitution')
    def replace_once(old, new):
        nonlocal top
        if top.count(old) != 1:
            raise ValueError('Unexpected top-level template: ' + old)
        top = top.replace(old, new)
    replace_once('    // HPS External Oscillator',
                 '    // Dedicated diagnostic connection to SOM clock/USB-mux I2C bus.\n'
                 '    inout wire cc_i2c_scl,\n    inout wire cc_i2c_sda,\n    // HPS External Oscillator')
    replace_once('    // Tie off all fabric to HPS interrupts', '''    wire [31:0] cc_probe_status;
    cc_reader #(.ALLOW_MODE_WRITES(MODE_WRITES_ENABLE)) u_cc_reader (
        .clk(sys_clk_100), .reset_n(sys_clk_100_reset_n),
        .trigger_toggle(fpga_leds[31]), .command(fpga_leds[10:8]), .byte_select(fpga_leds[7:4]),
        .usb_inputs({usb31_io_flt_bar, usb31_io_vbus_det, usb31_io_usb31_id}),
        .cc_scl(cc_i2c_scl), .cc_sda(cc_i2c_sda), .status(cc_probe_status)
    );

    // Tie off all fabric to HPS interrupts''')
    replace_once('.user_switches_export                 (fpga_switches)',
                 '.user_switches_export                 (cc_probe_status)')
    top = top.replace('MODE_WRITES_ENABLE', "1'b1" if args.enable_mode_writes else "1'b0")
    shutil.copytree(source, output, ignore=shutil.ignore_patterns(
        '.quartus', '.git', '__pycache__', 'dni', 'qdb', 'output_files', 'tmp-clearbox', '*.qdb', '*.qarlog', '*.qar_info.json',
        '*.rpt', '*.summary', '*.log', '*.dawf'))
    # This variant replaces the DIP-switch inputs; synthesis removes those
    # unused ports, so their former input-delay target is intentionally absent.
    sdc_path = output / 'baseline_a55.sdc'
    sdc = sdc_path.read_text()
    removed = [line for line in sdc.splitlines() if '[get_ports {fpga_user_switches[*]}]' in line]
    if len(removed) != 1:
        raise ValueError('Unexpected DIP-switch constraint template')
    sdc_path.write_text('\n'.join(line for line in sdc.splitlines() if line not in removed)+'\n')
    (output / 'baseline_a55.sv').write_text(top)
    shutil.copyfile(HERE / 'cc_reader.sv', output / 'src/cc_reader.sv')
    shutil.copyfile(HERE / 'cc-probe.sdc', output / 'cc-probe.sdc')
    with (output / 'baseline_a55.qsf').open('a') as handle:
        handle.write('''
# Isolated CC reader; SOM 150-0330723-B1 sheets 20/41, HVIO 6A 3.3 V.
set_global_assignment -name SYSTEMVERILOG_FILE src/cc_reader.sv
set_location_assignment PIN_BR28 -to cc_i2c_scl
set_location_assignment PIN_BR31 -to cc_i2c_sda
set_instance_assignment -name IO_STANDARD "3.3-V LVCMOS" -to cc_i2c_scl
set_instance_assignment -name IO_STANDARD "3.3-V LVCMOS" -to cc_i2c_sda
set_instance_assignment -name WEAK_PULL_UP_RESISTOR OFF -to cc_i2c_scl
set_instance_assignment -name WEAK_PULL_UP_RESISTOR OFF -to cc_i2c_sda
set_global_assignment -name SDC_FILE cc-probe.sdc
''')
    manifest = {
        'scope': 'Isolated Modular ES HD3SS3220 FPGA diagnostic; ' + ('limited volatile mode writes enabled' if args.enable_mode_writes else 'read-only'),
        'source_platform': str(source),
        'source_hashes': {name: digest(source/name) for name in (
            'baseline_a55.sv', 'baseline_a55.qsf', 'hps_subsys.qsys', 'fabric_subsys.qsys')},
        'diagnostic_hashes': {name: digest(HERE/name) for name in ('cc_reader.sv', 'cc-probe.sdc')},
        'pins': {'SCL': 'BR28', 'SDA': 'BR31'},
        'control': 'Existing LED PIO bit31 toggle starts read; bits7:4 select returned byte',
        'status': 'Existing switch PIO: done31, busy30, error29:26, fault25, VBUS24, ID23, SCL22, SDA21, tag19:16=0xc, data7:0',
        'target': '7-bit address 0x47, 11-byte identity/status read',
        'mode_writes_enabled': args.enable_mode_writes,
        'write_allowlist': '0x0a values 0x01, 0x21, 0x20, 0x00 only' if args.enable_mode_writes else 'none',
        'qualification': 'RTL simulated; physical qualification requires fitted image, matched handoff and fresh reads',
    }
    (output / 'cc-probe-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(output)

if __name__ == '__main__':
    main()
