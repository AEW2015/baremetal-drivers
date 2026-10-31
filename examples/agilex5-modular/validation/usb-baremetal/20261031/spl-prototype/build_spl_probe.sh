#!/usr/bin/env bash
# Cold-entry U-Boot SPL USB diagnostic: matching handoff, RAM-only second stage.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
base="$PWD/.deps/usb-uboot-source"
src="$PWD/.deps/usb-spl-probe-source"
out="$PWD/build/usb-spl-probe"
pin=e09d6fcc95f33b8a60377103f6e37e635660a3ee
[[ $(git -C "$base" rev-parse HEAD) == "$pin" ]]
if [[ ! -d "$src/.git" ]]; then git clone --shared --no-hardlinks "$base" "$src"; fi
[[ $(git -C "$src" rev-parse HEAD) == "$pin" ]]
python3 - "$src" <<'PATCH'
from pathlib import Path
import subprocess,sys
root=Path(sys.argv[1])
changes=subprocess.check_output(['git','-C',str(root),'diff','--name-only'],text=True).splitlines()
allowed=['arch/arm/mach-socfpga/spl_agilex5.c','arch/arm/mach-socfpga/spl_soc64.c']
assert all(p in allowed for p in changes),changes
for rel in allowed:
 original=subprocess.check_output(['git','-C',str(root),'show','HEAD:'+rel],text=True)
 if rel.endswith('spl_soc64.c'):
  marker='void board_boot_order(u32 *spl_boot_list)\n{'
  assert original.count(marker)==1
  patched=original.replace(marker,marker+'\n\t/* Isolated JTAG lab: never read a boot image from physical media. */\n\tspl_boot_list[0] = BOOT_DEVICE_RAM;\n\treturn;')
 else:
  marker='\t/* Enable non secure access to ocram */'
  assert original.count(marker)==1
  patched=original.replace(marker,r'''
	/* DDR is initialized by SPL before the host loads the RAM FIT.
	 * Reserved OCRAM handshake, below the matching handoff at 0x7f000.
	 */
	writel(0, (void *)0x7e000);
	puts("USB_SPL_PROBE_READY DDR initialized; awaiting RAM FIT\n");
	{
		ulong started = get_timer(0);
		while (readl((void *)0x7e000) != 0x55534231) {
			if (get_timer(started) > 240000) {
				puts("FAIL USB_SPL_PROBE host timeout\n");
				hang();
			}
		}
	}
	puts("USB_SPL_PROBE_CONTINUE RAM FIT only\n");

'''+marker)
 if rel.endswith('spl_agilex5.c'):
  patched='#include <time.h>\n'+patched
 actual=(root/rel).read_text()
 assert actual in (original,patched),rel
 (root/rel).write_text(patched)
PATCH
mkdir -p "$out"
make -C "$src" O="$out" CROSS_COMPILE=aarch64-linux-gnu- socfpga_agilex5_a0_modular_defconfig
"$src/scripts/config" --file "$out/.config" --disable TARGET_SOCFPGA_AGILEX5_SIMICS --disable TARGET_SOCFPGA_AGILEX5_EMU --disable SPL_WDT --disable SPL_WATCHDOG --enable SPL_RAM_DEVICE
make -C "$src" O="$out" CROSS_COMPILE=aarch64-linux-gnu- olddefconfig
make -C "$src" O="$out" CROSS_COMPILE=aarch64-linux-gnu- -j4 spl/u-boot-spl.bin
aarch64-linux-gnu-objcopy -I binary -O ihex --change-addresses 0 "$out/spl/u-boot-spl.bin" "$out/u-boot-spl.hex"
sha256sum "$out/spl/u-boot-spl.bin" "$out/u-boot-spl.hex"
