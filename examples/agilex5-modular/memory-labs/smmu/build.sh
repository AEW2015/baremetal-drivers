#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../.."
out=build/memory-smmu
mkdir -p "$out"
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
for variant in normal bypass keep-mapping; do
 flags=()
 [[ $variant != bypass ]] || flags+=(-DNEGATIVE_BYPASS)
 [[ $variant != keep-mapping ]] || flags+=(-DNEGATIVE_KEEP_MAPPING)
 "${prefix}gcc" -O1 -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 -mgeneral-regs-only \
  -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie -nostdlib -static \
  -Wl,--build-id=none,-T,qemu/labs/link.ld -Iqemu/labs "${flags[@]}" \
  qemu/labs/start.S qemu/labs/runtime.c memory-labs/smmu/main.c -o "$out/$variant.elf"
done
python3 - "$out" "$prefix" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[pathlib.Path(p) for p in ['memory-labs/smmu/main.c','memory-labs/smmu/build.sh','qemu/labs/start.S','qemu/labs/runtime.c','qemu/labs/lab.h','qemu/labs/link.ld']]
record={'scope':'QEMU virt SMMUv3 stage-2 + PCI EDU only; not Agilex DMA/TBU qualification',
        'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],
        'sources_sha256':{str(p):sha(p) for p in sources},
        'artifacts_sha256':{p.name:sha(p) for p in sorted(out.glob('*.elf'))}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
