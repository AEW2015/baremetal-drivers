#!/usr/bin/env bash
set -Eeuo pipefail
source_dir=$(cd "$(dirname "$0")" && pwd)
example_dir=$(cd "$source_dir/../.." && pwd)
cd "$example_dir"
: "${AGILEX_SOF:?Set AGILEX_SOF to a matching SOF, relative to examples/agilex5-modular or absolute}"
export AGILEX_SOF=$(python3 -c 'import os,pathlib; print(pathlib.Path(os.environ["AGILEX_SOF"]).resolve())')
output_dir=${AGILEX_DDR_BUILD_DIR:-build/boot}
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd)
atf_dir=${AGILEX_ATF_DIR:-build/deps/atf-26.3}
mkdir -p "$atf_dir"
atf_dir=$(cd "$atf_dir" && pwd)
cd "$output_dir"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
if [[ ! -d "$atf_dir/.git" ]]; then
    git clone --depth 1 --branch QPDS26.3_REL_BASELINE_PR https://github.com/altera-fpga/arm-trusted-firmware.git "$atf_dir"
fi
pin=$(python3 "$example_dir/release_pins.py" atf.commit)
[[ $(git -C "$atf_dir" rev-parse HEAD) == "$pin" ]]
aarch64-none-elf-gcc -nostdlib -Wl,-Ttext=0x82000000,-e,_start -o hello_ddr.elf "$source_dir/hello_ddr.S"
aarch64-none-elf-objcopy -O binary hello_ddr.elf hello_ddr.bin
export AGILEX_DDR_SOURCE_DIR="$source_dir"
python3 - <<'PY'
from pathlib import Path
import os
payload=','.join(hex(b) for b in Path('hello_ddr.bin').read_bytes())
bridge = ''
if os.environ.get('AGILEX_ENABLE_LWH2F', '0') == '1':
    bridge = '    if (intel_mailbox_is_fpga_not_ready()) { ERROR("LOCAL FABRIC: FPGA not ready\\n"); panic(); }\n    if (socfpga_bridges_enable(LWHPS2FPGA_MASK)) { ERROR("LOCAL FABRIC: bridge enable failed\\n"); panic(); }\n    NOTICE("LOCAL FABRIC: LWH2F enabled\\n");\n'
Path('local_ddr_probe.inc').write_text((Path(os.environ['AGILEX_DDR_SOURCE_DIR'])/'local_ddr_probe.inc.in').read_text().replace('PAYLOAD_BYTES',payload).replace('BRIDGE_ENABLE',bridge))
PY
if ! grep -q '#include "local_ddr_probe.inc"' "$atf_dir/plat/intel/soc/agilex5/bl2_plat_setup.c"; then
    git -C "$atf_dir" apply "$source_dir/atf-ddr-hook.patch"
fi
cp local_ddr_probe.inc "$atf_dir/plat/intel/soc/agilex5/"
make -C "$atf_dir" bl2 PLAT=agilex5 DEBUG=1 LOG_LEVEL=40 SOCFPGA_BOOT_SOURCE_QSPI=1 CROSS_COMPILE=aarch64-none-elf- -j4
aarch64-none-elf-objcopy -I binary -O ihex --change-addresses 0 "$atf_dir/build/agilex5/debug/bl2.bin" bl2-ddr.hex
# FPGA-first platforms require a complete merged image. HPS-only conversion is
# valid only when the source SOF was assembled for HPS-first configuration.
boot_order=${AGILEX_BOOT_ORDER:-fpga-first}
case "$boot_order" in fpga-first|hps-first) ;; *) echo 'Invalid AGILEX_BOOT_ORDER' >&2; exit 1;; esac
if [[ "$boot_order" == hps-first ]]; then
    quartus_pfg -c "$AGILEX_SOF" ddr_probe.rbf -o hps_path=bl2-ddr.hex -o hps=1
fi
export AGILEX_BOOT_ORDER="$boot_order"
quartus_pfg -c "$AGILEX_SOF" ddr_recovery.sof -o hps_path=bl2-ddr.hex
# Pair the generated images with their source and bridge-enable policy.
export AGILEX_RELEASE_PINS="$example_dir/release_pins.py"
export AGILEX_EXAMPLE_DIR="$example_dir"
python3 - <<'PYMETA'
from pathlib import Path
import os,json,hashlib
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
files=['ddr_recovery.sof']
if os.environ['AGILEX_BOOT_ORDER']=='hps-first':files.append('ddr_probe.hps.rbf')
Path('build-manifest.json').write_text(json.dumps({'boot_order':os.environ['AGILEX_BOOT_ORDER'],'atf_commit':__import__('subprocess').check_output(['python3',os.environ['AGILEX_RELEASE_PINS'],'atf.commit'],text=True).strip(),'lwh2f_enabled':os.environ.get('AGILEX_ENABLE_LWH2F','0')=='1','source_path_base':'examples/agilex5-modular','source_sof':os.path.relpath(os.environ['AGILEX_SOF'],os.environ['AGILEX_EXAMPLE_DIR']),'source_sof_sha256':sha(os.environ['AGILEX_SOF']),'images':{p:sha(p) for p in files}},indent=2)+'\n')
PYMETA
