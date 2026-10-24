#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
mkdir -p build
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -Wl,-T,core/link.ld -o build/core_examples.elf core/start.S core/fault.c core/core_examples.c
aarch64-none-elf-objcopy -O binary build/core_examples.elf build/core_examples.bin
