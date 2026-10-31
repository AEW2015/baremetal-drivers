#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../../.."
mkdir -p build/pr
"${CROSS_COMPILE:-aarch64-none-elf-}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
 -ffreestanding -fno-builtin -fno-pie -fno-stack-protector -nostdlib -static -no-pie \
 -DPR_PHYSICAL=1 -Wl,-T,core/link.ld -o build/pr/guest-hardware.elf \
 core/start.S core/fault.c fabric/pr/guest.c fabric/pr/pr_driver.c fabric/lab_driver.c fabric/lab_mmio.c
"${CROSS_COMPILE:-aarch64-none-elf-}objcopy" -O binary build/pr/guest-hardware.elf build/pr/guest-hardware.bin
