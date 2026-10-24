#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
compiler_prefix=${CROSS_COMPILE:-aarch64-none-elf-}
mkdir -p build/qemu-labs
build_one() {
 local name=$1 output=$2
 shift 2
 "${compiler_prefix}gcc" -Og -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 \
  -mgeneral-regs-only -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie \
  -nostdlib -static -Wl,--build-id=none,-T,qemu/labs/link.ld,-Map,build/qemu-labs/"$output".map \
  "$@" -o "build/qemu-labs/$output.elf" qemu/labs/start.S qemu/labs/runtime.c "qemu/labs/$name.c"
}
for name in startup corruption exception timer mmu uart; do build_one "$name" "$name"; done
# Negative controls: the host checker must reject each broken exercise.
build_one startup startup-no-bss -DSKIP_BSS_CLEAR
build_one startup startup-no-data -DSKIP_DATA_COPY
build_one corruption corruption-no-injection -DOMIT_CORRUPTION
build_one exception exception-wrong-brk -DWRONG_BRK
build_one timer timer-wrong-ppi -DEXPECT_TIMER_PPI=28
build_one mmu mmu-writable-ro -DWRITABLE_RO
