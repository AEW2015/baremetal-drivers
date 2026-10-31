#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/../../.."
out=build/memory-smmu-dmac
mkdir -p "$out"
prefix=${CROSS_COMPILE:-aarch64-none-elf-}
legacy=$(python3 legacy_source.py)
python3 - "$out/link.ld" <<'PY'
from pathlib import Path
import sys
s=Path('qemu/labs/link.ld').read_text()
for a,b in [('0x40200000','0x82400000'),('0x40300000','0x82500000'),('0x40400000','0x82600000'),('0x40500000','0x82700000'),('0x41000000','0x83fff000')]:s=s.replace(a,b)
Path(sys.argv[1]).write_text(s)
PY
"${prefix}gcc" -O1 -g3 -Wall -Wextra -Werror -mcpu=cortex-a53 -mgeneral-regs-only -mstrict-align \
 -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie -nostdlib -static \
 -DLAB_AGILEX5 -Iqemu/labs -I"$legacy/inc" -I"$legacy/inc/dma" \
 -Wl,--build-id=none,-T,"$out/link.ld",-Map,"$out/dmac-smmu.map" \
 qemu/labs/start.S qemu/labs/runtime.c memory-labs/smmu/dmac/main.c -o "$out/dmac-smmu.elf"
"${prefix}objcopy" -O binary "$out/dmac-smmu.elf" "$out/dmac-smmu.bin"
python3 - "$out" "$prefix" "$legacy" <<'PY'
import hashlib,json,subprocess,sys
from pathlib import Path
out=Path(sys.argv[1]);legacy=Path(sys.argv[3]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[Path(p) for p in ['memory-labs/smmu/dmac/main.c','memory-labs/smmu/dmac/build.sh','qemu/labs/start.S','qemu/labs/runtime.c','qemu/labs/lab.h','qemu/labs/link.ld']]
record={'target':'agilex5-simics-native-dmac','scope':'Compiled real DMAC0 guest; host-configured native SMMU stage2 fixture; no hardware qualification',
 'legacy_commit':subprocess.check_output(['git','-C',str(legacy),'rev-parse','HEAD'],text=True).strip(),
 'legacy_header_sha256':{p:sha(legacy/p) for p in ['inc/dma/dma_regs.h','inc/dma/dma.h','inc/hps_address_map.h']},
 'compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],
 'sources':{str(p):sha(p) for p in sources},'artifacts':{p.name:sha(p) for p in out.iterdir() if p.suffix in ('.elf','.bin')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n');print('PASS NATIVE_DMAC_SMMU_BUILD')
PY
