#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../../.."
mkdir -p build/pr
suffix=hardware
start=core/start.S
extra=()
if [[ "${1:-}" == hps ]]; then
 suffix=hps
 start=fabric/pr/hardware/start.S
 extra=(-DPR_HPS_SDM=1 fabric/pr/sdm_loader.c)
fi
"${CROSS_COMPILE:-aarch64-none-elf-}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
 -ffreestanding -fno-builtin -fno-pie -fno-stack-protector -nostdlib -static -no-pie \
 "${extra[@]}" -DPR_PHYSICAL=1 -Wl,-T,core/link.ld -o build/pr/guest-${suffix}.elf \
 "$start" core/fault.c fabric/pr/guest.c fabric/pr/pr_driver.c fabric/lab_driver.c fabric/lab_mmio.c
"${CROSS_COMPILE:-aarch64-none-elf-}objcopy" -O binary build/pr/guest-${suffix}.elf build/pr/guest-${suffix}.bin
