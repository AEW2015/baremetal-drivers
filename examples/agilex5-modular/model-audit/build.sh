#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
prefix=${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}
out=build/model-audit
mkdir -p "$out"
for name in pio mask-negative; do
  negative=0; [[ $name == pio ]] || negative=1
  "${prefix}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
    -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie -nostdlib -static \
    -DPIO_NEGATIVE="$negative" -Icore \
    -Wl,-T,core/link.ld,--build-id=none,-Map,"$out/$name.map" \
    core/start.S model-audit/pio.c core/fault.c -o "$out/$name.elf"
  "${prefix}objcopy" -O binary "$out/$name.elf" "$out/$name.bin"
done
python3 - "$out" "$prefix" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);root=pathlib.Path('.');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=[root/'model-audit/build.sh',root/'model-audit/pio.c',root/'core/start.S',root/'core/common.h',root/'core/fault.c',root/'core/link.ld']
record={'compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],
 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_sha256':{str(p):sha(p) for p in sources},'load_address':'0x82100000','entry_el':3,
 'scope':'Simics modeled LWHPS2FPGA PIO only; no physical I/O qualification',
 'artifacts':{p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ('.bin','.elf')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
