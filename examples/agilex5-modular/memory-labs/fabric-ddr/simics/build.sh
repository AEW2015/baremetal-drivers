#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../../.."
out="$PWD/build/fabric-ddr-simics"
mkdir -p "$out"
for security in secure nonsecure; do
 prot=0; subdir=rtl
 [[ $security == secure ]] || { prot=2; subdir=rtl-ns; }
 verilator --cc --exe --build --assert -Wall --top-module ddr_probe \
  -GALLOWED_BASE=64\'h85000000 -GALLOWED_END=64\'h85010000 -GAXPROT="3'h$prot" \
  --Mdir "$out/$subdir" "$PWD/memory-labs/fabric-ddr/rtl/ddr_probe.sv" \
  "$PWD/memory-labs/fabric-ddr/simics/transactor.cpp" > "$out/verilator-build-$security.log" 2>&1 || { cat "$out/verilator-build-$security.log"; exit 1; }
done
python3 - "$out/link.ld" <<'PY'
from pathlib import Path
import sys
s=Path('qemu/labs/link.ld').read_text()
for old,new in [('0x40200000','0x82400000'),('0x40300000','0x82500000'),('0x40400000','0x82600000'),('0x40500000','0x82700000'),('0x41000000','0x83fff000')]:s=s.replace(old,new)
Path(sys.argv[1]).write_text(s)
PY
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
for mode in physical translated fault read-fault timeout; do
 flags=()
 [[ $mode != translated && $mode != fault ]] || flags+=(-DTARGET_PHYSICAL=0x86000000UL)
 [[ $mode != fault ]] || flags+=(-DEXPECT_AXI_FAULT=1)
 [[ $mode != read-fault ]] || flags+=(-DEXPECT_DATA_FAULT=1)
 [[ $mode != timeout ]] || flags+=(-DEXPECT_TIMEOUT=1)
 "${prefix}gcc" -O2 -g -Wall -Wextra -Werror -mcpu=cortex-a53 -mgeneral-regs-only \
  -ffreestanding -fno-builtin -fno-pie -fno-stack-protector -nostdlib -static -no-pie \
  -DLAB_AGILEX5 -Iqemu/labs "${flags[@]}" -Wl,--build-id=none,-T,"$out/link.ld" \
  qemu/labs/start.S qemu/labs/runtime.c memory-labs/fabric-ddr/simics/guest.c \
  memory-labs/fabric-ddr/driver.c memory-labs/fabric-ddr/mmio.c -o "$out/$mode.elf"
 "${prefix}objcopy" -O binary "$out/$mode.elf" "$out/$mode.bin"
done
python3 - "$out" "$prefix" <<'PY'
from pathlib import Path
import sys,hashlib,json,subprocess
out=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[Path(p) for p in ['memory-labs/fabric-ddr/rtl/ddr_probe.sv','memory-labs/fabric-ddr/driver.c','memory-labs/fabric-ddr/driver.h','memory-labs/fabric-ddr/mmio.c','qemu/labs/start.S','qemu/labs/runtime.c','qemu/labs/lab.h','qemu/labs/link.ld']]
sources+=list(Path('memory-labs/fabric-ddr/simics').glob('*.cpp'))+list(Path('memory-labs/fabric-ddr/simics').glob('*.c'))+[Path('memory-labs/fabric-ddr/simics/build.sh')]
data={'scope':'Compiled actual RTL backend and bare-metal Arm guests; no execution claimed','compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],'verilator':subprocess.check_output(['verilator','--version'],text=True).strip(),'sources':{str(p):sha(p) for p in sources},'artifacts':{str(p.relative_to(out)):sha(p) for p in [*out.glob('*.elf'),*out.glob('*.bin'),out/'rtl/Vddr_probe',out/'rtl-ns/Vddr_probe']}}
(out/'build.json').write_text(json.dumps(data,indent=2)+'\n')
PY
