#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")"
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
mkdir -p build
aarch64-none-elf-gcc -Os -g -Wall -Wextra -Werror -ffreestanding -nostdlib -Wl,-T,uart_local.ld -o build/hello_uart.elf uart_start.S uart_local.c
aarch64-none-elf-objcopy -O binary build/hello_uart.elf build/hello_uart.bin
aarch64-none-elf-objcopy -I binary -O ihex build/hello_uart.bin build/hello_uart.hex
if [[ -n ${AGILEX_SOF:-} ]]; then
 quartus_pfg -c "$AGILEX_SOF" build/hello_uart.rbf -o hps_path=build/hello_uart.hex -o hps=1
fi
