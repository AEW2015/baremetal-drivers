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
import os
payload=','.join(hex(b) for b in Path('hello_ddr.bin').read_bytes())
bridge = ''
if os.environ.get('AGILEX_ENABLE_LWH2F', '0') == '1':
    bridge = '    if (intel_mailbox_is_fpga_not_ready()) { ERROR("LOCAL FABRIC: FPGA not ready\\n"); panic(); }\n    if (socfpga_bridges_enable(LWHPS2FPGA_MASK)) { ERROR("LOCAL FABRIC: bridge enable failed\\n"); panic(); }\n    NOTICE("LOCAL FABRIC: LWH2F enabled\\n");\n'
Path('local_ddr_probe.inc').write_text(Path('local_ddr_probe.inc.in').read_text().replace('PAYLOAD_BYTES',payload).replace('BRIDGE_ENABLE',bridge))
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
# Pair the generated images with their source and bridge-enable policy.
python3 - <<'PYMETA'
from pathlib import Path
import os,json,hashlib
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=['ddr_probe.hps.rbf','ddr_recovery.sof']
Path('build-manifest.json').write_text(json.dumps({'lwh2f_enabled':os.environ.get('AGILEX_ENABLE_LWH2F','0')=='1','source_sof':os.environ['AGILEX_SOF'],'source_sof_sha256':sha(os.environ['AGILEX_SOF']),'images':{p:sha(p) for p in files}},indent=2)+'\n')
PYMETA
