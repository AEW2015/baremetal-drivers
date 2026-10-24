#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
mkdir -p build
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
sed 's/0x82100000/0x82300000/;s/0x82200000, "Example/0x82400000, "Example/' core/link.ld > build/gic_link.ld
aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -Wl,-T,build/gic_link.ld -o build/gic_sgi.elf core/start.S core/fault.c core/gic_sgi.c
aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -c core/secondary_core.c -o build/secondary_core.o
