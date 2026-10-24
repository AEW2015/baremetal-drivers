# Start the provided debug-server.sh inside the Agilex container first.
set architecture aarch64
file build/core_examples.elf
target remote :3337
monitor halt
# Load after DDR initialization; the ELF's code address is 0x82100000.
load
hbreak example_main
set $pc=0x82100000
continue
info registers pc sp cpsr
# Step C code with next/step; inspect memory using x/16gx 0x85000000.
# To watch a scratch word: watch *(unsigned long long *)0x85010000
