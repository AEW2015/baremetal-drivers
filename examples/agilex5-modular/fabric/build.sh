#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
: "${LAB_CPU_BASE:?Set LAB_CPU_BASE to your verified CPU-visible CSR address (tutorial example 0x20020000)}"
[[ $LAB_CPU_BASE =~ ^0x[0-9a-fA-F]+$ ]] || { echo 'LAB_CPU_BASE must be hexadecimal' >&2; exit 1; }
mkdir -p build
"${CROSS_COMPILE:-aarch64-none-elf-}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
  -ffreestanding -fno-builtin -nostdlib -DLAB_CPU_BASE="$LAB_CPU_BASE" \
  -Wl,-T,core/link.ld -o build/fabric_example.elf core/start.S core/fault.c \
  fabric/fabric_example.c fabric/lab_driver.c fabric/lab_mmio.c
python3 - <<'PYMETA'
from pathlib import Path
import os,json,hashlib
elf=Path('build/fabric_example.elf')
Path('build/fabric-build.json').write_text(json.dumps({'cpu_base':int(os.environ['LAB_CPU_BASE'],16),'elf_sha256':hashlib.sha256(elf.read_bytes()).hexdigest()},indent=2)+'\n')
PYMETA
