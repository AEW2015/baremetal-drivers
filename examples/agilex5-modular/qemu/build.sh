#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
compiler_prefix=${CROSS_COMPILE:-aarch64-none-elf-}
mkdir -p build/qemu
"${compiler_prefix}gcc" -Og -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -static -Wl,--build-id=none,-T,qemu/link.ld -o build/qemu/hello.elf qemu/start.S qemu/hello.c
