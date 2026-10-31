#!/usr/bin/env bash
# Firmware builds only. No FPGA fit, simulator execution or physical board access.
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
for target in qemu agilex5; do
    bash memory-labs/dsu/build.sh "$target"
    bash memory-labs/ddr/build.sh "$target"
done
bash memory-labs/smmu/build.sh
echo 'PASS MEMORY_LAB_BUILDS: DSU/DDR QEMU + Agilex5, SMMU QEMU; execution is separate'
