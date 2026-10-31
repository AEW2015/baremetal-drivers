#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
out="$PWD/build/reference-hardware"
mkdir -p "$out"
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
"${prefix}gcc" -g -nostdlib -Wl,-Ttext=0x20000,-e,hello_entry,--build-id=none -o "$out/semihost.elf" bootstrap/ocram/hello_semihost.S
"${prefix}objcopy" -O binary "$out/semihost.elf" "$out/semihost.bin"
"${prefix}nm" -n "$out/semihost.elf" > "$out/symbols.txt"
# The read-only register probe is linked separately into existing DDR scratch.
sed 's/0x82100000/0x82500000/;s/0x82200000, "Example/0x82600000, "Example/' core/link.ld > "$out/fault.ld"
"${prefix}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only -ffreestanding -fno-builtin -nostdlib -Wl,-T,"$out/fault.ld" -o build/fault_probe.elf core/start.S core/fault.c core/fault_probe.c
