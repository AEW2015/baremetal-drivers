#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
mkdir -p build
for name in mmu_translation som_peripherals multicore som_i2c som_i3c mailbox_status som_interfaces fault_probe; do
 if [[ ! -f core/$name.c ]]; then continue; fi
 sed 's/0x82100000/0x82400000/;s/0x82200000, "Example/0x82500000, "Example/' core/link.ld > build/board_link.ld
 if [[ $name == fault_probe ]]; then
  sed 's/0x82100000/0x82500000/;s/0x82200000, "Example/0x82600000, "Example/' core/link.ld > build/board_link.ld
 fi
 extra=()
 if [[ $name == multicore ]]; then extra+=(core/secondary_start.S); fi
 aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -Wl,-T,build/board_link.ld -o "build/$name.elf" core/start.S core/fault.c "core/$name.c" "${extra[@]}"
done
if [[ ${SKIP_VENDOR:-0} != 1 ]]; then python3 build_board_vendor.py; fi
