#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
target=${1:-qemu}
[[ $target == qemu || $target == agilex5 ]] || { echo 'Choose qemu or agilex5' >&2; exit 2; }
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
out="build/dsu-$target"
mkdir -p "$out"
flags=()
[[ $target == agilex5 ]] && flags=(-DLAB_AGILEX5)
python3 - "$out/link.ld" "$target" <<'PY'
from pathlib import Path
import sys
s=Path('qemu/labs/link.ld').read_text()
if sys.argv[2]=='agilex5':
 for a,b in [('0x40200000','0x82400000'),('0x40300000','0x82500000'),('0x40400000','0x82600000'),('0x40500000','0x82700000'),('0x41000000','0x83fff000')]:s=s.replace(a,b)
Path(sys.argv[1]).write_text(s)
PY
variants=(normal corrupt stalled contention)
[[ $target == agilex5 ]] && variants+=(partitioned)
for variant in "${variants[@]}"; do
 extra=()
 [[ $variant == corrupt ]] && extra=(-DDSU_CORRUPT_PAYLOAD)
 [[ $variant == stalled ]] && extra=(-DDSU_OMIT_CONSUMER)
 [[ $variant == contention ]] && extra=(-DDSU_CONTENTION)
 [[ $variant == partitioned ]] && extra=(-DDSU_PARTITIONED -DDSU_CONTENTION)
 "$prefix"gcc -O2 -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 -mstrict-align \
  -mgeneral-regs-only -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie \
  -nostdlib -static -I qemu/labs -DLAB_MULTICORE "${flags[@]}" "${extra[@]}" \
  -Wl,--build-id=none,-T,"$out/link.ld",-Map,"$out/$variant.map" \
  -o "$out/$variant.elf" qemu/labs/start.S qemu/labs/runtime.c memory-labs/dsu/dsu.c
 "$prefix"objcopy -O binary "$out/$variant.elf" "$out/$variant.bin"
done
python3 - "$out" "$target" "$prefix" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[Path(p) for p in ['qemu/labs/start.S','qemu/labs/runtime.c','qemu/labs/lab.h','qemu/labs/link.ld','memory-labs/dsu/dsu.c','memory-labs/dsu/partition.h','memory-labs/dsu/contention.h','memory-labs/dsu/build.sh']]
record={'target':sys.argv[2],'scope':'Compile only; execution must be recorded separately','compiler':subprocess.check_output([sys.argv[3]+'gcc','--version'],text=True).splitlines()[0], 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'sources':{str(p):sha(p) for p in sources},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ['.elf','.bin']}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
print('PASS DSU_BUILD',sys.argv[2],out)
PY
