#!/usr/bin/env bash
# Build isolated pinned DDR bootstraps; never modify the qualified bench's ATF.
set -Eeuo pipefail
script_dir=$(cd "$(dirname "$0")" && pwd)
pack_dir=$(realpath "$script_dir/../../..")
work=$(realpath -m "${1:?Pass a new isolated output directory}")
atf_source=$(realpath "${2:?Pass a local clone of pinned ATF 26.3}")
[[ ! -e "$work" ]] || { echo 'Output exists; preserve previous attempts' >&2; exit 1; }
pin=$(python3 "$pack_dir/release_pins.py" atf.commit)
[[ $(git -C "$atf_source" rev-parse HEAD) == "$pin" ]]
mkdir -p "$work"
git clone --no-hardlinks --local "$atf_source" "$work/atf"
for f in hello_ddr.S atf-ddr-hook.patch local_ddr_probe.inc.in;do cp "$pack_dir/bootstrap/ddr/$f" "$work/$f";done
cp "$script_dir/bridge_enable.inc" "$work/bridge_enable.inc"
cd "$work"
aarch64-none-elf-gcc -nostdlib -Wl,-Ttext=0x82000000,-e,_start -o hello_ddr.elf hello_ddr.S
aarch64-none-elf-objcopy -O binary hello_ddr.elf hello_ddr.bin
if ! grep -q '#include "local_ddr_probe.inc"' atf/plat/intel/soc/agilex5/bl2_plat_setup.c;then git -C atf apply "$PWD/atf-ddr-hook.patch";fi
for variant in base bridge;do
 python3 - "$variant" <<'PY'
import sys
from pathlib import Path
payload=','.join(hex(b) for b in Path('hello_ddr.bin').read_bytes())
bridge=''
if sys.argv[1]=='bridge':bridge=Path('bridge_enable.inc').read_text()
Path('atf/plat/intel/soc/agilex5/local_ddr_probe.inc').write_text(Path('local_ddr_probe.inc.in').read_text().replace('PAYLOAD_BYTES',payload).replace('BRIDGE_ENABLE',bridge))
PY
 make -C atf bl2 PLAT=agilex5 DEBUG=1 LOG_LEVEL=40 SOCFPGA_BOOT_SOURCE_QSPI=1 CROSS_COMPILE=aarch64-none-elf- -j2
 cp atf/build/agilex5/debug/bl2.bin "bl2-$variant.bin"
 aarch64-none-elf-objcopy -I binary -O ihex --change-addresses 0 "bl2-$variant.bin" "bl2-$variant.hex"
done
