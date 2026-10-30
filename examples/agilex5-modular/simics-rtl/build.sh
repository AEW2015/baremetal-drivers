#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
if [[ -f /etc/profile.d/baremetal-tools.sh ]]; then source /etc/profile.d/baremetal-tools.sh; fi
out="${SIMICS_RTL_BUILD_DIR:-$PWD/build/simics-rtl}"
export SIMICS_RTL_BUILD_DIR="$out"
mkdir -p "$out"
for mode in 1 2; do
  verilator --cc --exe --build --assert -Wall --top-module lab_ip -GMODE="$mode" \
    --Mdir "$out/mode$mode" "$PWD/fabric/rtl/lab_ip.sv" "$PWD/fabric/rtl/lab_persona.sv" \
    "$PWD/simics-rtl/transactor.cpp" > "$out/verilator-mode$mode.log" 2>&1 || { cat "$out/verilator-mode$mode.log"; exit 1; }
done
for negative in 0 1; do
  "${CROSS_COMPILE:-aarch64-none-elf-}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
    -ffreestanding -fno-builtin -fno-pie -fno-stack-protector -nostdlib -static -no-pie -DEXPECT_TIMEOUT="$negative" \
    -Wl,-T,core/link.ld -o "$out/guest$negative.elf" core/start.S core/fault.c \
    simics-rtl/guest.c fabric/lab_driver.c fabric/lab_mmio.c
  "${CROSS_COMPILE:-aarch64-none-elf-}objcopy" -O binary "$out/guest$negative.elf" "$out/guest$negative.bin"
done
python3 - <<'PY'
import hashlib,json,os,subprocess
from pathlib import Path
root=Path.cwd();out=Path(os.environ['SIMICS_RTL_BUILD_DIR']).resolve()
files=[root/p for p in ['simics-rtl/transactor.cpp','simics-rtl/guest.c','simics-rtl/build.sh','fabric/lab_driver.c','fabric/lab_mmio.c','fabric/lab_driver.h','fabric/rtl/lab_ip.sv','fabric/rtl/lab_persona.sv','core/start.S','core/link.ld','core/fault.c','core/common.h']]
files+=list(out.glob('guest*.*'))+[out/'mode1/Vlab_ip',out/'mode2/Vlab_ip']
data={'scope':'Arm guest via Simics MMIO adapter to actual transaction-stepped Verilator RTL; no physical board/timing qualification','guest_compiler':subprocess.check_output([os.environ.get('CROSS_COMPILE','aarch64-none-elf-')+'gcc','--version'],text=True).splitlines()[0],'verilator':subprocess.check_output(['verilator','--version'],text=True).strip(),'sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
(out/'build.json').write_text(json.dumps(data,indent=2)+'\n');print('PASS SIMICS_RTL_BUILD: ADD1, XOR1, positive/negative AArch64 guests')
PY
