#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "$0")/.."
prefix=${UPSTREAM_CROSS_COMPILE:-aarch64-linux-gnu-}
out=build/config-audit
mkdir -p "$out"
sed 's/0x82100000/0x82400000/;s/0x82200000/0x82500000/' core/link.ld > "$out/link.ld"
for name in sysmgr pinmux unstable; do
  case=$([[ $name == sysmgr ]] && echo 0 || echo 1)
  extra=(); [[ $name != unstable ]] || extra=(-DAUDIT_INJECT_UNSTABLE)
  "${prefix}gcc" -Os -g -Wall -Wextra -Werror -mgeneral-regs-only \
    -ffreestanding -fno-builtin -fno-stack-protector -fno-pie -no-pie -nostdlib -static \
    -DAUDIT_CASE="$case" "${extra[@]}" -Icore -I../../platform/agilex5/include \
    -Wl,-T,"$out/link.ld",--build-id=none,-Map,"$out/$name.map" \
    config-audit/start.S config-audit/audit.c core/fault.c -o "$out/$name.elf"
  "${prefix}objcopy" -O binary "$out/$name.elf" "$out/$name.bin"
done
python3 - "$out" "$prefix" <<'PY'
import hashlib,json,pathlib,subprocess,sys
out=pathlib.Path(sys.argv[1]);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
sources=list(pathlib.Path('config-audit').glob('*'))+[pathlib.Path('core/common.h'),pathlib.Path('core/fault.c'),pathlib.Path('../../platform/agilex5/include/socfpga_sys_mngr_reg_plat.h')]
record={'compiler':subprocess.check_output([sys.argv[2]+'gcc','--version'],text=True).splitlines()[0],
 'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
 'source_sha256':{str(p):sha(p) for p in sources if p.is_file()},
 'load_address':'0x82400000','entry_el':3,'configuration_writes':False,
 'artifacts':{p.name:sha(p) for p in sorted(out.iterdir()) if p.suffix in ('.bin','.elf')}}
(out/'build.json').write_text(json.dumps(record,indent=2)+'\n')
PY
