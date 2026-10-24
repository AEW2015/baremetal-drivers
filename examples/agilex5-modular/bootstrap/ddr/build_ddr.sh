#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
: "${AGILEX_SOF:?Set AGILEX_SOF to the matching HPS-enabled Modular SOF}"
atf_dir=${AGILEX_ATF_DIR:-../atf-26.1.1}
if [[ ! -d "$atf_dir/.git" ]]; then
    git clone --depth 1 --branch QPDS26.1.1_REL_GSRD_PR https://github.com/altera-fpga/arm-trusted-firmware.git "$atf_dir"
fi
[[ $(git -C "$atf_dir" rev-parse HEAD) == 2ea5afda7f34774ddcc677fb3a728fa57f780a1e ]]
aarch64-none-elf-gcc -nostdlib -Wl,-Ttext=0x82000000,-e,_start -o hello_ddr.elf hello_ddr.S
aarch64-none-elf-objcopy -O binary hello_ddr.elf hello_ddr.bin
python3 - <<'PY'
from pathlib import Path
payload=','.join(hex(b) for b in Path('hello_ddr.bin').read_bytes())
Path('local_ddr_probe.inc').write_text(Path('local_ddr_probe.inc.in').read_text().replace('PAYLOAD_BYTES',payload))
PY
if ! grep -q '#include "local_ddr_probe.inc"' "$atf_dir/plat/intel/soc/agilex5/bl2_plat_setup.c"; then
    git -C "$atf_dir" apply "$(pwd)/atf-ddr-hook.patch"
fi
cp local_ddr_probe.inc "$atf_dir/plat/intel/soc/agilex5/"
make -C "$atf_dir" bl2 PLAT=agilex5 DEBUG=1 LOG_LEVEL=40 SOCFPGA_BOOT_SOURCE_QSPI=1 CROSS_COMPILE=aarch64-none-elf- -j4
aarch64-none-elf-objcopy -I binary -O ihex --change-addresses 0 "$atf_dir/build/agilex5/debug/bl2.bin" bl2-ddr.hex
quartus_pfg -c "$AGILEX_SOF" ddr_probe.rbf -o hps_path=bl2-ddr.hex -o hps=1
# Optional full volatile recovery image, with the same matching BL2 embedded.
quartus_pfg -c "$AGILEX_SOF" ddr_recovery.sof -o hps_path=bl2-ddr.hex
