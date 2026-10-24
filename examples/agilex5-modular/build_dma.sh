#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
mkdir -p build
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
sed 's/0x82100000/0x82200000/;s/0x82200000, "Example/0x82300000, "Example/' core/link.ld > build/dma_link.ld
aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -I../../inc -I../../inc/dma -Wl,-T,build/dma_link.ld -o build/dma_copy.elf core/start.S core/fault.c core/dma_copy.c
aarch64-none-elf-objcopy -O binary build/dma_copy.elf build/dma_copy.bin
