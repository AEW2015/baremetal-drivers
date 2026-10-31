#!/usr/bin/env python3
"""Restore vendor BL2 USB PIPE-power setup in the isolated reset-to-BL31 lab monitor."""
import argparse
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--spl-reset-pulse', action='store_true',
                        help='Opt-in U-Boot SPL compatibility experiment; TF-A reverted this bit after FreeRTOS enumeration issues')
    args = parser.parse_args()
    relative = 'plat/intel/soc/agilex5/bl31_plat_setup.c'
    original = subprocess.check_output(['git', '-C', str(args.source), 'show', 'HEAD:' + relative]).decode()
    marker = '\tsetup_smmu_stream_id();\n'
    assert original.count(marker) == 1
    addition = '''
#if RESET_TO_BL31
	/* Normal vendor BL2 setup is bypassed by the DDR-only lab bootstrap.
	 * Match bl2_plat_setup.c: set USB3 PIPE power present, preserving other bits.
	 */
	uint32_t usb_misc_before = mmio_read_32(SOCFPGA_SYSMGR(USB3_MISC_CTRL_REG0));
	mmio_write_32(SOCFPGA_SYSMGR(USB3_MISC_CTRL_REG0),
		     usb_misc_before | SYSMGR_USB3_MISC0_PORT_OVR_CURR_PIPE_PWR);
	INFO("USB_LAB_MONITOR USB3_MISC0 before=%08x after=%08x mask=%08x\\n",
	     usb_misc_before, mmio_read_32(SOCFPGA_SYSMGR(USB3_MISC_CTRL_REG0)),
	     (unsigned int)SYSMGR_USB3_MISC0_PORT_OVR_CURR_PIPE_PWR);
#endif
'''
    previous = original.replace(marker, marker + addition)
    addition = addition.replace('	uint32_t usb_misc_before', '	INFO("USB_LAB_MONITOR PER0MODRST before=%08x\\n",\n	     mmio_read_32(SOCFPGA_RSTMGR(PER0MODRST)));\n	uint32_t usb_misc_before')
    addition = addition.replace('#endif', '	INFO("USB_LAB_MONITOR PER0MODRST after=%08x\\n",\n	     mmio_read_32(SOCFPGA_RSTMGR(PER0MODRST)));\n#endif')
    previous_reset_logs = original.replace(marker, marker + addition)
    clock_snapshot = '''
	/* Read-only clock diagnostics. Register enables do not prove a physical
	 * PHY/PIPE clock is toggling; preserve the handoff's clock programming.
	 */
	INFO("USB_LAB_MONITOR CLKMGR_STAT=%08x USB31CTR=%08x EXTCNTRST=%08x\\n",
	     mmio_read_32(CLKMGR(STAT)),
	     mmio_read_32(CLKMGR_ALTERA(USB31CTR)),
	     mmio_read_32(CLKMGR_ALTERA(EXTCNTRST)));
'''
    patched = original.replace('#include "agilex5_cache.h"',
                               '#include "agilex5_cache.h"\n#include "agilex5_clock_manager.h"')
    patched = patched.replace(marker, marker + addition.replace('#endif', clock_snapshot + '#endif'))
    spl_variant = patched.replace(
        'SYSMGR_USB3_MISC0_PORT_OVR_CURR_PIPE_PWR',
        '(SYSMGR_USB3_MISC0_PORT_OVR_CURR_PIPE_PWR | SYSMGR_USB3_MISC0_RST_PUL_OVRD)')
    spl_variant = spl_variant.replace(
        'Match bl2_plat_setup.c: set USB3 PIPE power present, preserving other bits.',
        'EXPERIMENT: match pinned U-Boot SPL reset override + PIPE power present.\n'
        '\t * TF-A reverted bit12 after FreeRTOS enumeration problems; not a universal fix.')
    spl_variant = spl_variant.replace(
        '\tuint32_t usb_misc_before',
        '\tINFO("USB_LAB_MONITOR EXPERIMENT=UBOOT_SPL_RESET_PULSE bit12=1; TF-A reverted for FreeRTOS enumeration\\n");\n'
        '\tuint32_t usb_misc_before')
    path = args.source / relative
    if path.read_text() not in (original, previous, previous_reset_logs, patched, spl_variant):
        raise RuntimeError('Unexpected USB monitor source modification')
    path.write_text(spl_variant if args.spl_reset_pulse else patched)
    print('PASS USB_MONITOR_PATCH: '+('EXPERIMENT U-Boot SPL bit12+14 compatibility' if args.spl_reset_pulse else 'normal vendor USB3 PIPE-power-present initialization'))


if __name__ == '__main__':
    main()
